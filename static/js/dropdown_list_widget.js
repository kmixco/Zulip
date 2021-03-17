import $ from "jquery";

import render_dropdown_list from "../templates/settings/dropdown_list.hbs";

import * as ListWidget from "./list_widget";

export const DropdownListWidget = function (opts) {
    const init = () => {
        // Run basic sanity checks on opts, and set up sane defaults.
        opts = {
            multiselect: false,
            null_value: null,
            render_text: (item_name) => item_name,
            on_update: () => {},
            ...opts,
        };
        opts.container_id = `${opts.widget_name}_widget`;
        opts.value_id = `id_${opts.widget_name}`;
        if (opts.value === undefined) {
            opts.value = opts.null_value;
            blueslip.warn("dropdown-list-widget: Called without a default value; using null value");
        }
        if (opts.multiselect) {
            opts.selected_values = []; // Populate the values selected by user.
        }
    };
    init();

    const render = (value) => {
        $(`#${CSS.escape(opts.container_id)} #${CSS.escape(opts.value_id)}`).data("value", value);

        let text = "";
        const elem = $(`#${CSS.escape(opts.container_id)} #${CSS.escape(opts.widget_name)}_name`);

        if (!value || value === opts.null_value) {
            elem.text(opts.default_text);
            elem.addClass("text-warning");
            elem.closest(".input-group").find(".dropdown_list_reset_button:enabled").hide();
            return;
        }

        // Happy path

        if (opts.multiselect && Array.isArray(value)) {
            const limit = opts.multiselect.limit;
            let data_list = value;

            if (data_list.length === 0) {
                data_list = [opts.value.toString()];
            }
            if (limit < data_list.length) {
                text = `${data_list.length} selected`;
            } else {
                const selected_data = opts.data.filter((x) => data_list.includes(x.value));
                text = selected_data.map((data) => data.name).toString();
            }
        } else {
            const item = opts.data.find((x) => x.value === value.toString());
            text = opts.render_text(item.name);
        }
        elem.text(text);
        elem.removeClass("text-warning");
        elem.closest(".input-group").find(".dropdown_list_reset_button:enabled").show();
    };

    const update = (value) => {
        render(value);
        opts.on_update(value);
    };

    const register_event_handlers = () => {
        const add_check_mark = (element, value) => {
            const link_elem = element.find("a").expectOne();
            element.addClass("checked");
            link_elem.prepend('<i class="fa fa-check" aria-hidden="true"></i>');
            opts.selected_values.push(value);
        };

        const remove_check_mark = (element, value) => {
            const icon = element.find("i").expectOne();
            const index = opts.selected_values.indexOf(value);
            if (index > -1) {
                icon.remove();
                element.removeClass("checked");
                opts.selected_values.splice(index, 1);
            }
        };

        const click_handler = $(`#${CSS.escape(opts.container_id)} .dropdown-list-body`);

        if (opts.multiselect) {
            click_handler.on("click keypress", ".list_item", function (e) {
                const value = $(this).attr("data-value");

                if ($(this).hasClass("checked")) {
                    remove_check_mark($(this), value);
                } else {
                    add_check_mark($(this), value);
                }

                e.stopPropagation();
            });
        } else {
            click_handler.on("click keypress", ".list_item", function (e) {
                const setting_elem = $(this).closest(`.${CSS.escape(opts.widget_name)}_setting`);
                if (e.type === "keypress") {
                    if (e.which === 13) {
                        setting_elem.find(".dropdown-menu").dropdown("toggle");
                    } else {
                        return;
                    }
                }
                const value = $(this).attr("data-value");
                update(value);
            });
        }
        $(`#${CSS.escape(opts.container_id)} .dropdown_list_reset_button`).on("click", (e) => {
            update(opts.null_value);
            e.preventDefault();
        });

        $(`#${CSS.escape(opts.container_id)} .multiselect_btn`).on("click", (e) => {
            const value = opts.selected_values;
            update(value);
            e.preventDefault();
        });
    };

    const setup = () => {
        // populate the dropdown
        const dropdown_list_body = $(
            `#${CSS.escape(opts.container_id)} .dropdown-list-body`,
        ).expectOne();
        const search_input = $(
            `#${CSS.escape(opts.container_id)} .dropdown-search > input[type=text]`,
        );
        const dropdown_toggle = $(`#${CSS.escape(opts.container_id)} .dropdown-toggle`);

        ListWidget.create(dropdown_list_body, opts.data, {
            name: `${CSS.escape(opts.widget_name)}_list`,
            modifier(item) {
                return render_dropdown_list({item});
            },
            filter: {
                element: search_input,
                predicate(item, value) {
                    return item.name.toLowerCase().includes(value);
                },
                multiselect: {
                    selected_items: opts.selected_values,
                },
            },
            simplebar_container: $(`#${CSS.escape(opts.container_id)} .dropdown-list-wrapper`),
        });
        $(`#${CSS.escape(opts.container_id)} .dropdown-search`).on("click", (e) => {
            e.stopPropagation();
        });

        dropdown_toggle.on("click", () => {
            search_input.val("").trigger("input");
        });

        dropdown_toggle.on("focus", (e) => {
            // On opening a Bootstrap Dropdown, the parent element receives focus.
            // Here, we want our search input to have focus instead.
            e.preventDefault();
            search_input.trigger("focus");
        });

        search_input.on("keydown", (e) => {
            if (!/(38|40|27)/.test(e.keyCode)) {
                return;
            }
            e.preventDefault();
            const custom_event = new $.Event("keydown.dropdown.data-api", {
                keyCode: e.keyCode,
                which: e.keyCode,
            });
            dropdown_toggle.trigger(custom_event);
        });

        render(opts.value);
        register_event_handlers();
    };

    const value = () => {
        let val = $(`#${CSS.escape(opts.container_id)} #${CSS.escape(opts.value_id)}`).data(
            "value",
        );
        if (val === null) {
            val = "";
        }
        return val;
    };

    // Run setup() automatically on initialization.
    setup();

    return {
        render,
        value,
        update,
    };
};
