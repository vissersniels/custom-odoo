/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { checkFileSize } from "@web/core/utils/files";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
import { FileUploader } from "@web/views/fields/file_handler";

import { useState } from "@odoo/owl";

export class DragDropBinaryField extends BinaryField {
    static template = "outstanding_order_comparison.DragDropBinaryField";
    static components = {
        FileUploader,
    };

    setup() {
        super.setup();
        this.state = useState({
            isDragging: false,
            isUploading: false,
        });
    }

    async uploadFiles(fileList) {
        const files = Array.from(fileList || []);
        if (!files.length) {
            return;
        }
        for (const file of files) {
            if (!checkFileSize(file.size, this.notification)) {
                return;
            }
            this.state.isUploading = true;
            const data = await getDataURLFromFile(file);
            if (!file.size) {
                this.notification.add(_t("There was a problem while uploading your file."), {
                    type: "danger",
                });
                continue;
            }
            await this.update({
                name: file.name,
                data: data.split(",")[1],
            });
        }
        this.state.isUploading = false;
    }

    onDragEnter(ev) {
        ev.preventDefault();
        this.state.isDragging = true;
    }

    onDragOver(ev) {
        ev.preventDefault();
        this.state.isDragging = true;
    }

    onDragLeave(ev) {
        ev.preventDefault();
        const currentTarget = ev.currentTarget;
        const relatedTarget = ev.relatedTarget;
        if (!currentTarget || !relatedTarget || !currentTarget.contains(relatedTarget)) {
            this.state.isDragging = false;
        }
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.state.isDragging = false;
        await this.uploadFiles(ev.dataTransfer?.files);
    }
}

export const dragDropBinaryField = {
    ...binaryField,
    component: DragDropBinaryField,
};

registry.category("fields").add("drag_drop_binary", dragDropBinaryField);