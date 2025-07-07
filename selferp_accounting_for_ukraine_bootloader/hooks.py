import os
import psycopg2
import shutil
import tempfile
import threading
import zipfile

from odoo import _
from odoo.exceptions import UserError
from odoo.http import root
from odoo.modules.module import load_manifest, check_manifest_dependencies
from odoo.service import server
from odoo.tools import config
from odoo.tools.misc import file_path


def post_init_hook(env):
    _unpack_loader(env)


def _unpack_loader(env):
    if getattr(threading.current_thread(), 'testing', False):
        raise RuntimeError("Module operations inside tests are not transactional and thus forbidden.")

    try:
        # This is done because the installation/uninstallation/upgrade can modify a currently
        # running cron job and prevent it from finishing, and since the ir_cron table is locked
        # during execution, the lock won't be released until timeout.
        env.cr.execute("SELECT * FROM ir_cron FOR UPDATE NOWAIT")
    except psycopg2.OperationalError:
        raise UserError(_(
            "Odoo is currently processing a scheduled action.\n"
            "Module operations are not possible at this time, "
            "please try again later or contact your system administrator."
        ))

    # get loader archive file path
    loader_file = file_path('selferp_accounting_for_ukraine_bootloader/data/modules.zip')
    module_names = []

    # WO: replace restart function to prevent autoreload sources
    _restart = server.restart
    server.restart = lambda: None

    try:
        # check destination module dir
        apps_path = config.addons_data_dir
        # @TODO: maybe get current permissions and return them back finally ?
        if not os.path.exists(apps_path):
            parent_path = apps_path.rpartition(os.sep)[0]
            os.chmod(parent_path, 0o700)
            os.makedirs(apps_path, mode=0o700, exist_ok=True)
        else:
            os.chmod(apps_path, 0o700)

        with tempfile.TemporaryDirectory() as temp_dir:
            # unpack all into temp dir
            with zipfile.ZipFile(loader_file, 'r') as archive:
                archive.extractall(temp_dir)

            for module_path in os.listdir(temp_dir):
                # get module name and remember it for update later
                module_name = os.path.split(module_path)[-1]
                module_names.append(module_name)

                # remove existing dir if exists
                destination_path = os.path.join(apps_path, module_name)
                if os.path.exists(destination_path):
                    shutil.rmtree(destination_path)

                # move new dir
                shutil.move(os.path.join(temp_dir, module_path), destination_path)
    finally:
        # return restart function back
        server.restart = _restart

    # update modules list
    IrModuleModule = env['ir.module.module']
    IrModuleModule.update_list()

    # mark to update already installed modules
    # add not yet installed loader modules
    modules = IrModuleModule.search([
        ('name', 'in', module_names),
    ])
    if not modules:
        raise UserError(_("An installation error occurred, restart your Odoo instance and try installing the module again. If the error occurs again, contact your Administrator or the support service."))

    to_update = modules.filtered(lambda r: r.state == 'installed')
    to_install = (modules - to_update).filtered(lambda r: r.state == 'uninstalled')

    if to_update:
        to_update.write({
            'state': 'to upgrade',
        })

        # check each module
        dependencies = []
        for module in to_update:
            # get manifest
            manifest = load_manifest(module.name)

            # check external dependencies
            check_manifest_dependencies(manifest)

            # remember dependencies
            dependencies += manifest.get('depends') or []

        # check dependencies existing
        dependencies = list(set(dependencies))
        to_install += IrModuleModule.search([
            ('name', 'in', dependencies),
            ('state', '=', 'uninstalled'),
        ])

    # install immediately
    if to_install:
        to_install.button_install()

    # save all changes
    env.cr.commit()

    # clear static cache
    if hasattr(root, 'statics') and root.statics:
        del root.statics
