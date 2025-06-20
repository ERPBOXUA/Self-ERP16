import json
import io
import zipfile

from werkzeug.exceptions import NotFound

from odoo.http import route, request, Controller, content_disposition


class AccountMoveController(Controller):

    @route('/account_move/vat/download_xml/<string:move_ids>', auth='user', sitemap=False)
    def account_move_vat_download_xml(self, move_ids, **kwargs):
        if move_ids:
            # get all moves by IDs
            moves = request.env['account.move'].search([
                ('id', 'in', json.loads(move_ids)),
                ('move_type', 'in', ('vat_invoice', 'vat_adjustment_invoice')),
            ])

            if moves:
                if len(moves) == 1:
                    # create data (single XML)
                    file_name, data = moves.vat_create_xml()

                    # return result
                    return request.make_response(
                        data,
                        headers={
                            ('Content-Type', 'application/xml'),
                            ('Content-Length', len(data)),
                            ('Content-Disposition', content_disposition(file_name)),
                        },
                    )

                else:
                    # create data (ZIP)
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                        for move in moves:
                            file_name, data = move.vat_create_xml()
                            zip_file.writestr(file_name, data)

                    zip_data = zip_buffer.getvalue()

                    # determine file name
                    zip_name = ''
                    if moves.filtered(lambda r: r.move_type == 'vat_invoice'):
                        zip_name += 'ПН'
                    if moves.filtered(lambda r: r.move_type == 'vat_adjustment_invoice'):
                        if zip_name:
                            zip_name += '+'
                        zip_name += 'РК'
                    zip_name += '.zip'

                    # return result
                    return request.make_response(
                        zip_data,
                        headers={
                            ('Content-Type', 'application/zip'),
                            ('Content-Length', len(zip_data)),
                            ('Content-Disposition', content_disposition(zip_name)),
                        },
                    )

        raise NotFound()

