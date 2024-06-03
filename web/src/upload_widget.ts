import {Uppy} from "@uppy/core";
import Dashboard from "@uppy/dashboard";
import type {DashboardOptions} from "@uppy/dashboard";
import type {ImageEditorOptions} from "@uppy/image-editor";
import ImageEditor from "@uppy/image-editor";
import $ from "jquery";

import * as dialog_widget from "./dialog_widget";
import {$t, $t_html} from "./i18n";
import * as loading from "./loading";
import {any_active} from "./modals";
import * as settings_data from "./settings_data";

const default_max_file_size = 5;

// These formats do not need to be universally understood by clients; they are all
// converted, server-side, currently to PNGs.  This list should be kept in sync with
// the THUMBNAIL_ACCEPT_IMAGE_TYPES in zerver/lib/thumbnail.py
const supported_types = [
    "image/avif",
    "image/gif",
    "image/heic",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
];

let uppy: Uppy;
let edited_file: File;
let original_file: File;
// This ID is used to remove file from Uppy dashboard.
// In order to removed the form that is created each time an image is uploaded.
let fileID: string;

export function get_edited_file(): File {
    return edited_file;
}

export type UploadWidget = {
    clear: () => void;
    close: () => void;
};

export type UploadFunction = (
    $file_input: {files: File[]},
    night: boolean | null,
    icon: boolean,
) => void;

export type CropperOptions = {
    aspectRatio: number;
    cropSquare: boolean;
};

function upload_direct_widget(
    file: File,
    upload_function: UploadFunction,
    $upload_button: JQuery,
): void {
    const $realm_logo_section = $upload_button.closest(".image_upload_widget");
    if ($realm_logo_section.attr("id") === "realm-night-logo-upload-widget") {
        upload_function({files: [file]}, true, false);
    } else if ($realm_logo_section.attr("id") === "realm-day-logo-upload-widget") {
        upload_function({files: [file]}, false, false);
    } else {
        upload_function({files: [file]}, null, true);
    }
    if (any_active()) {
        dialog_widget.close();
    }
}

function is_image_format(file: File): boolean {
    const type = file.type;
    if (!type) {
        return false;
    }
    return supported_types.includes(type);
}

function hide_elements(selectors: string[]): (HTMLElement | SVGElement)[] {
    const hidden_elements: (HTMLElement | SVGElement)[] = [];
    const interval_id = setInterval(() => {
        let all_elements_found = true;
        for (const selector of selectors) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                for (const element of elements) {
                    if (element instanceof HTMLElement || element instanceof SVGElement) {
                        element.style.visibility = "hidden";
                        hidden_elements.push(element);
                    }
                }
            } else {
                all_elements_found = false;
            }
        }
        if (all_elements_found) {
            // Stop checking once all elements are found and hidden
            clearInterval(interval_id);
        }
    }, 2); // Check every 2 milliseconds
    return hidden_elements;
}

function display_dashboard_after_timeout(is_build_widget: boolean): void {
    const $dashboard_element = $(".uppy-Dashboard-inner");
    if ($dashboard_element.length && $dashboard_element[0] instanceof HTMLElement) {
        $dashboard_element.css("visibility", "hidden");
    }
    loading.make_indicator($("#image_loading_indicator"), {
        text: $t({defaultMessage: "Loading…"}),
    });

    const selectors = [
        ".uppy-u-reset.uppy-c-btn",
        ".uppy-u-reset.uppy-Dashboard-Item-action.uppy-Dashboard-Item-action--remove",
        'svg.uppy-c-icon[aria-hidden="true"]',
        ".modal__footer",
        ...(is_build_widget ? ["#image_editor"] : []),
    ];
    const hidden_elements = hide_elements(selectors);

    // Duration (in milliseconds) to hide the dashboard and other specified elements
    const timeout = 1500;
    setTimeout(() => {
        if ($dashboard_element.length && $dashboard_element[0] instanceof HTMLElement) {
            $dashboard_element.css("visibility", "visible");
        }
        loading.destroy_indicator($("#image_loading_indicator"));
        for (const element of hidden_elements) {
            element.style.visibility = "visible";
        }
    }, timeout);
}

const dashboard_options: DashboardOptions = {
    id: "Dashboard",
    inline: true,
    autoOpenFileEditor: true,
    animateOpenClose: false,
    hideUploadButton: true,
};

const image_editor_options: ImageEditorOptions = {
    id: "ImageEditor",
    quality: 1,
    target: Dashboard,
    cropperOptions: {
        viewMode: 1,
        aspectRatio: 1,
        background: true,
        cropBoxResizable: true,
        movable: true,
        restore: true,
        responsive: false,
        zoomOnWheel: false,
        croppedCanvasOptions: {},
        dragMode: "none",
    },
    actions: {
        cropSquare: true,
        cropWidescreen: false,
        cropWidescreenVertical: false,
        zoomIn: false,
        zoomOut: false,
        revert: false,
        rotate: false,
        granularRotate: false,
        flip: false,
    },
    locale: {
        strings: {
            aspectRatioSquare: "Reset",
        },
    },
};

async function is_image_scalable(file: File): Promise<boolean> {
    return new Promise((resolve) => {
        const image = new Image();
        image.addEventListener("load", function () {
            if (image_editor_options.cropperOptions?.aspectRatio === 1) {
                resolve(this.width !== this.height);
            } else {
                // aspect ratio is 4
                resolve(this.width / this.height !== 4);
            }
        });
        image.src = URL.createObjectURL(file);
    });
}

async function scale_image(file: File): Promise<File> {
    return new Promise((resolve, reject) => {
        const image = new Image();

        image.addEventListener("load", function () {
            const image_width = this.width;
            const image_height = this.height;

            const canvas = document.createElement("canvas");
            if (image_editor_options.cropperOptions?.aspectRatio === 1) {
                canvas.width = 1000;
                canvas.height = 1000;
            } else {
                // aspect ratio is 4
                canvas.width = 1000;
                canvas.height = 250;
            }

            // draw the scaled image on the canvas
            const context = canvas.getContext("2d");
            if (context) {
                context.drawImage(
                    image,
                    0,
                    0,
                    image_width,
                    image_height,
                    0,
                    0,
                    canvas.width,
                    canvas.height,
                );
            }

            // convert the canvas to a blob and return it
            canvas.toBlob((blob) => {
                if (blob) {
                    resolve(new File([blob], file.name, {type: file.type}));
                } else {
                    reject(new Error("Failed to scale image"));
                }
            }, file.type);
        });

        image.src = URL.createObjectURL(file);
    });
}

export function build_widget(
    // function returns a jQuery file input object
    get_file_input: () => JQuery<HTMLInputElement>,
    // jQuery object to show file name
    $file_name_field: JQuery,
    // jQuery object for error text
    $input_error: JQuery,
    // jQuery button to clear last upload choice
    $clear_button: JQuery,
    // jQuery button to open file dialog
    $upload_button: JQuery,
    $save_button: JQuery,
    $scale_to_fit_button: JQuery,
    $reset_scale_to_fit_button: JQuery,
    cropper_options: CropperOptions,
    $preview_text?: JQuery,
    $preview_image?: JQuery,
    $other_elements_to_hide?: JQuery,
    max_file_upload_size = default_max_file_size,
): UploadWidget {
    let first = true;
    let reset_scale = false;
    let edited = false;
    let alternate_button = false;
    let scalable = true;
    async function accept(file: File): Promise<void> {
        if (image_editor_options.cropperOptions && image_editor_options.actions) {
            image_editor_options.cropperOptions.aspectRatio = cropper_options.aspectRatio;
            image_editor_options.actions.cropSquare = cropper_options.cropSquare;
        }
        if (first) {
            scalable = await is_image_scalable(file);
            first = false;
        }
        $file_name_field.text(file.name);
        if ($preview_text && $preview_image) {
            $preview_image.addClass("upload_widget_image_preview");
            // uppy does not allow cropping of giffs, the emoji would become an image
            if (file.type === "image/gif" && $file_name_field.is("#emoji-file-name")) {
                const image_blob = URL.createObjectURL(file);
                $preview_image.attr("src", image_blob);
                $upload_button.hide();
                $clear_button.show();
            } else {
                $file_name_field.hide();
                $input_error.hide();
                $upload_button.hide();
                $preview_image?.hide();
                $other_elements_to_hide?.hide();
                $preview_text.show();
                $save_button.show();
                if (scalable) {
                    if (!alternate_button) {
                        $scale_to_fit_button.show();
                        $reset_scale_to_fit_button.hide();
                    } else {
                        $scale_to_fit_button.hide();
                        $reset_scale_to_fit_button.show();
                    }
                }
                $clear_button.show();

                uppy = new Uppy({
                    restrictions: {
                        allowedFileTypes: supported_types,
                        maxNumberOfFiles: 1,
                        maxFileSize: max_file_upload_size * 1024 * 1024,
                    },
                })
                    .use(Dashboard, {
                        ...dashboard_options,
                        target: "#" + $preview_text.attr("id"),
                        theme: settings_data.using_dark_theme() ? "dark" : "light",
                    })
                    .use(ImageEditor, image_editor_options)
                    .on("file-editor:complete", () => {
                        const file = uppy.getFiles()[0];
                        if (file) {
                            fileID = file.id;
                            if (edited) {
                                edited = false;
                                alternate_button = !alternate_button;
                                uppy.removeFile(fileID);
                                uppy.close();
                                if (reset_scale) {
                                    void accept(original_file);
                                } else {
                                    void accept(edited_file);
                                }
                                reset_scale = !reset_scale;
                            } else {
                                edited_file = new File([file.data], file.name);
                                const image_blob = URL.createObjectURL(edited_file);
                                $preview_image.attr("src", image_blob);
                                uppy.close();
                                $input_error.hide();
                                $save_button.hide();
                                $scale_to_fit_button.hide();
                                $reset_scale_to_fit_button.hide();
                                $preview_image?.show();
                                $file_name_field.show();
                                $other_elements_to_hide?.show();
                                if (!$file_name_field.closest("#emoji-file-name").length) {
                                    $clear_button.hide();
                                }
                            }
                        }
                    });

                uppy.addFile({
                    source: "file input",
                    name: file.name,
                    type: file.type,
                    data: file,
                });

                display_dashboard_after_timeout(true);
            }
        }
    }

    function clear(): void {
        if (uppy) {
            uppy.close();
        }
        const $control = get_file_input();
        $control.val("");
        $file_name_field.text("");
        $save_button.hide();
        $scale_to_fit_button.hide();
        $reset_scale_to_fit_button.hide();
        $input_error.hide();
        $other_elements_to_hide?.show();
        $clear_button.hide();
        $upload_button.show();
        first = true;
    }

    $clear_button.on("click", (e) => {
        clear();
        e.preventDefault();
    });

    $save_button.on("click", (e) => {
        $(".uppy-DashboardContent-save").trigger("click");
        e.preventDefault();
    });

    $scale_to_fit_button.on("click", (e) => {
        edited = true;
        $(".uppy-DashboardContent-save").trigger("click");
        e.preventDefault();
    });

    $reset_scale_to_fit_button.on("click", (e) => {
        edited = true;
        $(".uppy-DashboardContent-save").trigger("click");
        e.preventDefault();
    });

    $upload_button.on("drop", (e) => {
        const files = e.originalEvent?.dataTransfer?.files;
        if (files === null || files === undefined || files.length === 0) {
            return false;
        }
        const $file_input = get_file_input();
        if ($file_input[0]) {
            $file_input[0].files = files;
        }
        e.preventDefault();
        return false;
    });

    get_file_input().attr("accept", supported_types.toString());
    get_file_input().on("change", (e) => {
        if (e.target.files?.[0] === undefined) {
            $input_error.hide();
        } else if (e.target.files?.length === 1) {
            const file = e.target.files[0];
            if (file) {
                if (file.size > max_file_upload_size * 1024 * 1024) {
                    $input_error.text(
                        $t(
                            {defaultMessage: "File size must be at most {max_file_size} MiB."},
                            {max_file_size: max_file_upload_size},
                        ),
                    );
                    $input_error.show();
                    clear();
                } else if (!is_image_format(file)) {
                    $input_error.text($t({defaultMessage: "File type is not supported."}));
                    $input_error.show();
                    clear();
                } else {
                    reset_scale = false;
                    alternate_button = false;
                    original_file = file;
                    void scale_image(original_file).then((scaled_file) => {
                        edited_file = scaled_file;
                    });
                    void accept(original_file);
                }
            }
        } else {
            $input_error.text($t({defaultMessage: "Please just upload one file."}));
        }
    });

    $upload_button.on("click", (e) => {
        get_file_input().trigger("click");
        e.preventDefault();
    });

    function close(): void {
        clear();
        $clear_button.off("click");
        $upload_button.off("drop");
        get_file_input().off("change");
        $upload_button.off("click");
        $save_button.off("click");
    }

    return {
        // Call back to clear() in situations like adding bots, when
        // we want to use the same widget over and over again.
        clear,
        // Call back to close() when you are truly done with the widget,
        // so you can release handlers.
        close,
    };
}

export function build_direct_upload_widget(
    // function returns a jQuery file input object
    get_file_input: () => JQuery<HTMLInputElement>,
    // jQuery object for error text
    $input_error: JQuery,
    // jQuery button to open file dialog
    $upload_button: JQuery,
    upload_function: UploadFunction,
    // default value of max uploaded file size
    max_file_upload_size: number,
    // New profile picture or New organization logo or New organization icon
    heading: string,
    // Cropper options passed by the caller
    cropper_options: CropperOptions,
): void {
    let first = true;
    let reset_scale = false;
    let edited = false;
    let scalable = true;
    function submit(): void {
        $(".uppy-DashboardContent-save").trigger("click");
    }

    function clear(): void {
        if (uppy) {
            uppy.close();
        }
        const $control = get_file_input();
        $control.val("");
        first = true;
    }

    async function accept(file: File): Promise<void> {
        $input_error.hide();
        if (first) {
            first = false;
            dialog_widget.launch({
                html_heading: heading,
                html_body: "<div id='ImageEditorDiv'></div>",
                html_submit_button: `${$t_html({
                    defaultMessage: "Save changes",
                })} <button class='modal__btn hide direct_widget_save' id='scale_to_fit'>Scale to fit</button> <button class='modal__btn hide direct_widget_save' id='reset_scale_to_fit'>Reset scale</button>`,
                on_click: submit,
                on_hidden: clear,
            });

            const $scaleButton = $("#scale_to_fit");
            const $resetButton = $("#reset_scale_to_fit");

            $scaleButton.on("click", (e) => {
                edited = true;
                $(".uppy-DashboardContent-save").trigger("click");
                $scaleButton.hide();
                $resetButton.show();
                e.preventDefault();
            });

            $resetButton.on("click", (e) => {
                edited = true;
                $(".uppy-DashboardContent-save").trigger("click");
                $scaleButton.show();
                $resetButton.hide();
                e.preventDefault();
            });

            if (image_editor_options.cropperOptions && image_editor_options.actions) {
                image_editor_options.cropperOptions.aspectRatio = cropper_options.aspectRatio;
                image_editor_options.actions.cropSquare = cropper_options.cropSquare;
            }

            scalable = await is_image_scalable(file);
            if (scalable) {
                $scaleButton.show();
            }
        }

        uppy = new Uppy({
            restrictions: {
                allowedFileTypes: supported_types,
                maxNumberOfFiles: 1,
                maxFileSize: max_file_upload_size * 1024 * 1024,
            },
        })
            .use(Dashboard, {
                ...dashboard_options,
                target: "#ImageEditorDiv",
                theme: settings_data.using_dark_theme() ? "dark" : "light",
            })
            .use(ImageEditor, image_editor_options)
            .on("file-editor:complete", () => {
                const file = uppy.getFiles()[0];
                if (file) {
                    fileID = file.id;
                    if (edited) {
                        edited = false;
                        uppy.removeFile(fileID);
                        uppy.close();
                        if (reset_scale) {
                            void accept(original_file);
                        } else {
                            void accept(edited_file);
                        }
                        reset_scale = !reset_scale;
                    } else {
                        upload_direct_widget(
                            new File([file.data], file.name),
                            upload_function,
                            $upload_button,
                        );
                    }
                } else {
                    clear();
                    $input_error.hide();
                }
            });

        uppy.addFile({
            name: file.name,
            type: file.type,
            data: file,
        });

        display_dashboard_after_timeout(false);
    }

    $upload_button.on("drop", (e) => {
        const files = e.originalEvent?.dataTransfer?.files;
        if (files === null || files === undefined || files.length === 0) {
            return false;
        }
        const $file_input = get_file_input();
        if ($file_input[0]) {
            $file_input[0].files = files;
        }
        e.preventDefault();
        return false;
    });

    get_file_input().attr("accept", supported_types.toString());
    get_file_input().on("change", (e) => {
        if (e.target.files?.length === 0) {
            $input_error.hide();
        } else if (e.target.files?.length === 1) {
            const file = e.target.files[0];
            if (file) {
                if (file.size > max_file_upload_size * 1024 * 1024) {
                    $input_error.text(
                        $t(
                            {defaultMessage: "File size must be at most {max_file_size} MiB."},
                            {max_file_size: max_file_upload_size},
                        ),
                    );
                    $input_error.show();
                    clear();
                } else if (!is_image_format(file)) {
                    $input_error.text($t({defaultMessage: "File type is not supported."}));
                    $input_error.show();
                    clear();
                } else {
                    reset_scale = false;
                    original_file = file;
                    void scale_image(original_file).then((scaled_file) => {
                        edited_file = scaled_file;
                    });
                    void accept(original_file);
                }
            }
        } else {
            $input_error.text($t({defaultMessage: "Please just upload one file."}));
        }
    });

    $upload_button.on("click", (e) => {
        get_file_input().trigger("click");
        e.preventDefault();
    });
}
