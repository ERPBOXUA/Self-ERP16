odoo.define('selferp_l10n_ua_ext.account_editable_report', function (require) {
'use strict';


const core = require('web.core');
const publicWidget = require('web.public.widget');
const Dialog = require('web.Dialog');


const _t = core._t;


publicWidget.registry.AccountEditableReport = publicWidget.Widget.extend({
    selector: 'form.account_editable_report_form',


    willStart: function ()
    {
        const self = this;

        return this._super.apply(arguments).then(function ()
        {
            self._bindTables();
        });
    },


    start: function ()
    {
        const self = this;

        return this._super.apply(arguments).then(function ()
        {
            if (self.$('input[name="saved"]').val())
            {
                Dialog.alert(self, _t("Successfully saved"), {
                    title: _t("Saved"),
                });
            }
        });
    },


    _bindTables: function ()
    {
        const self = this;
        self.tables = {};

        // get unique editable tables
        this.$('.selferp_table_row_editable').each(function ()
        {
            const $row = $(this);

            const dataKey = $row.data('key');
            if (!self.tables[dataKey])
            {
                const $table = $row.closest('table');

                $table.addClass('selferp_table_editable')
                    .data('key', dataKey)
                    .data('minRowCount', $row.data('minRowCount'));

                self.tables[dataKey] = $table;
            }

            self._bindRow($row);
        });

        // for each table add new row button at the right bottom corner
        _.each(Object.keys(self.tables), function (tableKey)
        {
            self._bindAddButton(tableKey);
        })
    },


    _bindAddButton: function (tableKey)
    {
        const $addButton = $('<a>', {
            href: 'javascript:void(0);',
            title: _t("Add new row"),
            class: 'selferp_table_row_add',
        });
        $addButton.data('key', tableKey);
        $addButton.prepend($('<i class="fa fa-plus-circle" aria-hidden="true"></i>'));
        $addButton.on('click', this._onAddRow.bind(this));

        const $container = $('<div>', {class: 'selferp_table_row_add_container'});
        $addButton.appendTo($container);

        const $lastRow = this._getAllRowsByKey(tableKey).last();
        $($lastRow.find('td:last-child')[0]).prepend($container);
    },


    _bindRow: function ($row)
    {
        const self = this;
        const tableKey = $row.data('key');

        // add remove button
        const $removeButton = $('<a>', {
            href: 'javascript:void(0);',
            title: _t("Remove row"),
            class: 'selferp_table_row_remove',
        });
        $removeButton.data('key', tableKey);
        $removeButton.prepend($('<i class="fa fa-minus-circle" aria-hidden="true"></i>'));
        $removeButton.on('click', self._onRemoveRow.bind(self));

        const $container = $('<div>', {class: 'selferp_table_row_remove_container'});
        $removeButton.appendTo($container);
        $($row.find('td:last-child')[0]).prepend($container);
    },




    _getAllRowsByKey: function (tableKey)
    {
        return this.tables[tableKey].find('.selferp_table_row_editable[data-key="' + tableKey + '"]');
    },


    _clearAllInputValues: function ($parent)
    {
        $parent.find(':input').each(function()
        {
            switch(this.type)
            {
                case 'text':
                case 'textarea':
                case 'password':
                case 'file':
                case 'select-one':
                case 'select-multiple':
                case 'date':
                case 'number':
                case 'tel':
                case 'email':
                    $(this).removeAttr('value').val('');
                    break;
                case 'checkbox':
                case 'radio':
                    $(this).removeAttr('checked');
                    this.checked = false;
                    break;
            }
        });
    },

    _updateRowIndex: function ($row, index)
    {
        // update row number (if exists)
        $row.find('.selferp_table_row_number').empty().text(index + 1);

        // update inputs name
        $row.find(':input').each(function ()
        {
            const $input = $(this);
            let name = $input.attr('name');
            name = name.substring(0, name.lastIndexOf('_') + 1);
            $input.attr('name', name + index);
        });
    },




    _onRemoveRow: function (event)
    {
        event.preventDefault();
        event.stopImmediatePropagation();

        const self = this;
        const $row = $(event.target).closest('.selferp_table_row_editable');

        // get all table rows
        const tableKey = $row.data('key');
        let $rows = this._getAllRowsByKey(tableKey);

        if ($rows.length > (parseInt($row.data('minRowCount')) || 2))
        {
            const last = ($rows.index($row) == $rows.length - 1);

            // remove row
            $row.remove();

            // get all rows
            $rows = this._getAllRowsByKey(tableKey);

            // update row index
            $rows.each(function (index)
            {
                self._updateRowIndex($(this), index);
            });

            // put add button back
            if (last)
            {
                this._bindAddButton(tableKey);
            }
        }
        else
        {
            // clear all values in row
            this._clearAllInputValues($row);
        }
    },


    _onAddRow: function (event)
    {
        event.preventDefault();
        event.stopImmediatePropagation();

        // get current state
        const $addButton = $(event.currentTarget);
        const $row = $addButton.closest('.selferp_table_row_editable');
        const tableKey = $row.data('key');
        const $rows = this._getAllRowsByKey(tableKey);

        // create and prepare new row
        $addButton.closest('.selferp_table_row_add_container').remove();
        const $newRow = $row.clone();
        $newRow.find('.selferp_table_row_remove_container').remove();
        this._clearAllInputValues($newRow);
        this._updateRowIndex($newRow, $rows.length);
        this._bindRow($newRow);

        // add new row into the table
        $newRow.insertAfter($rows.last());

        // bind add button
        this._bindAddButton(tableKey);
    },


});



});
