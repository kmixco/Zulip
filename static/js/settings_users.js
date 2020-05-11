const settings_data = require("./settings_data");
const render_admin_user_list = require("../templates/admin_user_list.hbs");
const render_bot_owner_select = require("../templates/bot_owner_select.hbs");
const render_admin_human_form = require('../templates/admin_human_form.hbs');
const render_admin_bot_form = require('../templates/admin_bot_form.hbs');

const meta = {
    loaded: false,
};

exports.reset = function () {
    meta.loaded = false;
};

const section = {
    active: {},
    deactivated: {},
    bots: {},
};

function compare_a_b(a, b) {
    if (a > b) {
        return 1;
    } else if (a === b) {
        return 0;
    }
    return -1;
}

function sort_email(a, b) {
    const email_a = settings_data.email_for_user_settings(a) || '';
    const email_b = settings_data.email_for_user_settings(b) || '';
    return compare_a_b(
        email_a.toLowerCase(),
        email_b.toLowerCase()
    );
}

function sort_role(a, b) {
    function role(user) {
        if (user.is_admin) { return 0; }
        if (user.is_guest) { return 2; }
        return 1; // member
    }
    return compare_a_b(role(a), role(b));
}

function sort_bot_owner(a, b) {
    function owner_name(item) {
        const owner = people.get_bot_owner_user(item);

        if (!owner) {
            return '';
        }

        if (!owner.full_name) {
            return '';
        }

        return owner.full_name.toLowerCase();
    }

    return compare_a_b(
        owner_name(a),
        owner_name(b)
    );
}

function sort_last_active(a, b) {
    return compare_a_b(
        presence.last_active_date(a.id) || 0,
        presence.last_active_date(b.id) || 0
    );
}

function get_user_info_row(user_id) {
    return $("tr.user_row[data-user-id='" + user_id + "']");
}

function update_view_on_deactivate(row) {
    const button = row.find("button.deactivate");
    const user_role = row.find(".user_role");
    button.prop("disabled", false);
    row.find('button.open-user-form').hide();
    row.find('i.deactivated-user-icon').show();
    button.addClass("btn-warning reactivate");
    button.removeClass("deactivate btn-danger");
    button.html("<i class='fa fa-user-plus' aria-hidden='true'></i>");
    button.attr('title', 'Reactivate');
    row.addClass("deactivated_user");

    if (user_role) {
        const user_id = row.data('user-id');
        user_role.text("%state (%role)".replace("%state", i18n.t("Deactivated")).
            replace("%role", people.get_user_type(user_id)));
    }
}

function update_view_on_reactivate(row) {
    const button = row.find("button.reactivate");
    const user_role = row.find(".user_role");
    row.find("button.open-user-form").show();
    row.find('i.deactivated-user-icon').hide();
    button.addClass("btn-danger deactivate");
    button.removeClass("btn-warning reactivate");
    button.attr('title', 'Deactivate');
    button.html('<i class="fa fa-user-plus" aria-hidden="true"></i>');
    row.removeClass("deactivated_user");

    if (user_role) {
        const user_id = row.data('user-id');
        user_role.text(people.get_user_type(user_id));
    }
}

function get_status_field() {
    const current_tab = settings_panel_menu.org_settings.current_tab();
    switch (current_tab) {
    case 'deactivated-users-admin':
        return $("#deactivated-user-field-status").expectOne();
    case 'user-list-admin':
        return $("#user-field-status").expectOne();
    case 'bot-list-admin':
        return $("#bot-field-status").expectOne();
    default:
        blueslip.fatal("Invalid admin settings page");
    }
}

function failed_listing_users(xhr) {
    loading.destroy_indicator($('#subs_page_loading_indicator'));
    const status = get_status_field();
    ui_report.error(i18n.t("Error listing users or bots"), xhr, status);
}

function populate_users(realm_people_data) {
    let active_users = [];
    let deactivated_users = [];
    let bots = [];
    for (const user of realm_people_data.members) {
        if (user.is_bot) {
            bots.push(user);
        } else if (user.is_active) {
            active_users.push(user);
        } else {
            deactivated_users.push(user);
        }
    }

    active_users = _.sortBy(active_users, 'full_name');
    deactivated_users = _.sortBy(deactivated_users, 'full_name');
    bots = _.sortBy(bots, 'full_name');

    section.active.create_table(active_users);
    section.deactivated.create_table(deactivated_users);
    section.bots.create_table(bots);
}

function reset_scrollbar($sel) {
    return function () {
        ui.reset_scrollbar($sel);
    };
}

function bot_owner_full_name(owner_id) {
    if (!owner_id) {
        return;
    }

    const bot_owner = people.get_by_user_id(owner_id);
    if (!bot_owner) {
        return;
    }

    return bot_owner.full_name;
}

function bot_info(bot_user) {
    const owner_id = bot_user.bot_owner_id;

    const info = {};

    info.is_bot = true;
    info.is_admin = false;
    info.is_guest = false;
    info.is_active = bot_user.is_active;
    info.user_id = bot_user.user_id;
    info.full_name = bot_user.full_name;
    info.bot_owner_id = owner_id;

    // Convert bot type id to string for viewing to the users.
    info.bot_type = settings_bots.type_id_to_string(bot_user.bot_type);

    info.bot_owner_full_name = bot_owner_full_name(owner_id);

    if (!info.bot_owner_full_name) {
        info.no_owner = true;
        info.bot_owner_full_name = i18n.t("No owner");
    }

    info.is_current_user = false;
    info.can_modify = page_params.is_admin;

    // It's always safe to show the fake email addresses for bot users
    info.display_email = bot_user.email;

    return info;
}

function get_last_active(user) {
    const last_active_date = presence.last_active_date(user.user_id);

    if (!last_active_date) {
        return i18n.t("Unknown");
    }
    return timerender.render_now(last_active_date).time_str;
}

function human_info(person) {
    const info = {};

    info.is_bot = false;
    info.is_admin = person.is_admin;
    info.is_guest = person.is_guest;
    info.is_active = person.is_active;
    info.user_id = person.user_id;
    info.full_name = person.full_name;
    info.bot_owner_id = person.bot_owner_id;

    info.can_modify = page_params.is_admin;
    info.is_current_user = people.is_my_user_id(person.user_id);
    info.display_email = settings_data.email_for_user_settings(person);

    if (person.is_active) {
        // TODO: We might just want to show this
        // for deactivated users, too, even though
        // it might usually just be undefined.
        info.last_active_date = get_last_active(person);
    }

    return info;
}

section.bots.create_table = (bots) => {
    const $bots_table = $("#admin_bots_table");
    list_render.create($bots_table, bots, {
        name: "admin_bot_list",
        modifier: function (bot_user) {
            const info = bot_info(bot_user);
            return render_admin_user_list(info);
        },
        filter: {
            element: $bots_table.closest(".settings-section").find(".search"),
            predicate: function (item, value) {
                return item.full_name.toLowerCase().includes(value) ||
                item.email.toLowerCase().includes(value);
            },
            onupdate: reset_scrollbar($bots_table),
        },
        parent_container: $("#admin-bot-list").expectOne(),
        init_sort: ['alphabetic', 'full_name'],
        sort_fields: {
            email: sort_email,
            bot_owner: sort_bot_owner,
        },
    });

    loading.destroy_indicator($('#admin_page_bots_loading_indicator'));
    $("#admin_bots_table").show();
};

section.active.create_table = (active_users) => {
    const $users_table = $("#admin_users_table");
    list_render.create($users_table, active_users, {
        name: "users_table_list",
        modifier: function (item) {
            const info = human_info(item);
            return render_admin_user_list(info);
        },
        filter: {
            element: $users_table.closest(".settings-section").find(".search"),
            filterer: people.filter_for_user_settings_search,
            onupdate: reset_scrollbar($users_table),
        },
        parent_container: $("#admin-user-list").expectOne(),
        init_sort: ['alphabetic', 'full_name'],
        sort_fields: {
            email: sort_email,
            last_active: sort_last_active,
            role: sort_role,
        },
    });

    loading.destroy_indicator($('#admin_page_users_loading_indicator'));
    $("#admin_users_table").show();
};

section.deactivated.create_table = (deactivated_users) => {
    const $deactivated_users_table = $("#admin_deactivated_users_table");
    list_render.create($deactivated_users_table, deactivated_users, {
        name: "deactivated_users_table_list",
        modifier: function (item) {
            const info = human_info(item);
            return render_admin_user_list(info);
        },
        filter: {
            element: $deactivated_users_table.closest(".settings-section").find(".search"),
            filterer: people.filter_for_user_settings_search,
            onupdate: reset_scrollbar($deactivated_users_table),
        },
        parent_container: $("#admin-deactivated-users-list").expectOne(),
        init_sort: ['alphabetic', 'full_name'],
        sort_fields: {
            email: sort_email,
            role: sort_role,
        },
    });

    loading.destroy_indicator($('#admin_page_deactivated_users_loading_indicator'));
    $("#admin_deactivated_users_table").show();
};

exports.update_user_data = function (user_id, new_data) {
    if (!meta.loaded) {
        return;
    }

    const user_row = get_user_info_row(user_id);

    if (new_data.full_name !== undefined) {
        // Update the full name in the table
        user_row.find(".user_name").text(new_data.full_name);
    }

    if (new_data.owner_id !== undefined) {
        // TODO: Linkify the owner name to match the
        //       formatting of the list. Ideally we can
        //       make this whole function simpler
        //       by re-rendering the entire row via
        //       the list widget.
        const owner_name = bot_owner_full_name(new_data.owner_id);
        user_row.find(".owner").text(owner_name);
    }

    if (new_data.is_active !== undefined) {
        if (new_data.is_active === false) {
            // Deactivate the user/bot in the table
            update_view_on_deactivate(user_row);
        } else {
            // Reactivate the user/bot in the table
            update_view_on_reactivate(user_row);
        }
    }

    if (new_data.is_admin !== undefined || new_data.is_guest !== undefined) {
        user_row.find(".user_role").text(people.get_user_type(user_id));
    }
};

function start_data_load() {
    loading.make_indicator($('#admin_page_users_loading_indicator'), {text: 'Loading...'});
    loading.make_indicator($('#admin_page_bots_loading_indicator'), {text: 'Loading...'});
    loading.make_indicator($('#admin_page_deactivated_users_loading_indicator'), {text: 'Loading...'});
    $("#admin_deactivated_users_table").hide();
    $("#admin_users_table").hide();
    $("#admin_bots_table").hide();

    // Populate users and bots tables
    channel.get({
        url: '/json/users',
        idempotent: true,
        timeout: 10 * 1000,
        success: exports.on_load_success,
        error: failed_listing_users,
    });
}

function open_human_form(person) {
    const user_id = person.user_id;

    const html = render_admin_human_form({
        user_id: user_id,
        email: person.email,
        full_name: person.full_name,
        is_admin: person.is_admin,
        is_guest: person.is_guest,
        is_member: !person.is_admin && !person.is_guest,
    });
    const div = $(html);
    const modal_container = $('#user-info-form-modal-container');
    modal_container.empty().append(div);
    overlays.open_modal('#admin-human-form');

    const element = "#admin-human-form .custom-profile-field-form";
    $(element).html("");
    settings_account.append_custom_profile_fields(element, user_id);
    settings_account.initialize_custom_date_type_fields(element);
    const pills = settings_account.initialize_custom_user_type_fields(
        element,
        user_id,
        true,
        false
    );

    return {
        modal: div,
        fields_user_pills: pills,
    };
}

function get_human_profile_data(fields_user_pills) {
    /*
        This formats custom profile field data to send to the server.
        See render_admin_human_form and open_human_form
        to see how the form is built.

        TODO: Ideally, this logic would be cleaned up or deduplicated with
        the settings_account.js logic.
    */
    const new_profile_data = [];
    $("#admin-human-form .custom_user_field_value").each(function () {
        // Remove duplicate datepicker input element generated flatpicker library
        if (!$(this).hasClass("form-control")) {
            new_profile_data.push({
                id: parseInt($(this).closest(".custom_user_field").attr("data-field-id"), 10),
                value: $(this).val(),
            });
        }
    });
    // Append user type field values also
    for (const [field_id, field_pills] of  fields_user_pills) {
        if (field_pills) {
            const user_ids = user_pill.get_user_ids(field_pills);
            new_profile_data.push({
                id: field_id,
                value: user_ids,
            });
        }
    }

    return new_profile_data;
}

function open_bot_form(person) {
    const html = render_admin_bot_form({
        user_id: person.user_id,
        email: person.email,
        full_name: person.full_name,
    });
    const div = $(html);
    const modal_container = $('#user-info-form-modal-container');
    modal_container.empty().append(div);
    overlays.open_modal('#admin-bot-form');

    // NOTE: building `users_list` is quite expensive!
    const users_list = people.get_active_humans();
    const owner_select = $(render_bot_owner_select({users_list: users_list}));
    owner_select.val(bot_data.get(person.user_id).owner || "");
    modal_container.find(".edit_bot_owner_container").append(owner_select);

    return div;
}

function confirm_deactivation(row, user_id, status_field) {
    const modal_elem = $("#deactivation_user_modal").expectOne();

    function set_fields() {
        const user = people.get_by_user_id(user_id);
        modal_elem.find(".email").text(user.email);
        modal_elem.find(".user_name").text(user.full_name);
    }

    function handle_confirm() {
        const row = get_user_info_row(user_id);

        modal_elem.modal("hide");
        const row_deactivate_button = row.find("button.deactivate");
        row_deactivate_button.prop("disabled", true).text(i18n.t("Working…"));
        const opts = {
            success_continuation: function () {
                update_view_on_deactivate(row);
            },
            error_continuation: function () {
                row_deactivate_button.text(i18n.t("Deactivate"));
            },
        };
        const url = '/json/users/' + encodeURIComponent(user_id);
        settings_ui.do_settings_change(channel.del, url, {}, status_field, opts);

    }

    modal_elem.modal("hide");
    modal_elem.off('click', '.do_deactivate_button');
    set_fields();
    modal_elem.on('click', '.do_deactivate_button', handle_confirm);
    modal_elem.modal("show");
}

function handle_deactivation(tbody, status_field) {
    tbody.on("click", ".deactivate", function (e) {
        // This click event must not get propagated to parent container otherwise the modal
        // will not show up because of a call to `close_active_modal` in `settings.js`.
        e.preventDefault();
        e.stopPropagation();

        const row = $(e.target).closest(".user_row");
        const user_id = row.data('user-id');
        confirm_deactivation(row, user_id, status_field);
    });
}

function handle_bot_deactivation(tbody, status_field) {
    tbody.on("click", ".deactivate", function (e) {
        e.preventDefault();
        e.stopPropagation();

        const button_elem = $(e.target);
        const row = button_elem.closest(".user_row");
        const bot_id = parseInt(row.attr("data-user-id"), 10);
        const url = '/json/bots/' + encodeURIComponent(bot_id);

        const opts = {
            success_continuation: function () {
                update_view_on_deactivate(row);
            },
            error_continuation: function (xhr) {
                ui_report.generic_row_button_error(xhr, button_elem);
            },
        };
        settings_ui.do_settings_change(channel.del, url, {}, status_field, opts);

    });
}

function handle_reactivation(tbody, status_field) {
    tbody.on("click", ".reactivate", function (e) {
        e.preventDefault();
        e.stopPropagation();
        // Go up the tree until we find the user row, then grab the email element
        const button_elem = $(e.target);
        const row = button_elem.closest(".user_row");
        const user_id = parseInt(row.attr("data-user-id"), 10);
        const url = '/json/users/' + encodeURIComponent(user_id) + "/reactivate";
        const data = {};

        const opts = {
            success_continuation: function () {
                update_view_on_reactivate(row);
            },
            error_continuation: function (xhr) {
                ui_report.generic_row_button_error(xhr, button_elem);
            },
        };

        settings_ui.do_settings_change(channel.post, url, data, status_field, opts);
    });
}

function handle_bot_owner_profile(tbody) {
    tbody.on('click', '.user_row .view_user_profile', function (e) {
        const owner_id = parseInt($(e.target).attr('data-owner-id'), 10);
        const owner = people.get_by_user_id(owner_id);
        popovers.show_user_profile(owner);
        e.stopPropagation();
        e.preventDefault();
    });
}

function handle_human_form(tbody, status_field) {
    tbody.on("click", ".open-user-form", function (e) {
        const user_id = parseInt($(e.currentTarget).attr("data-user-id"), 10);
        const person = people.get_by_user_id(user_id);

        if (!person) {
            return;
        }

        const ret = open_human_form(person);
        const modal = ret.modal;
        const fields_user_pills = ret.fields_user_pills;

        modal.find('.submit_human_change').on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();

            const user_role_select_value = modal.find('#user-role-select').val();
            const full_name = modal.find("input[name='full_name']");
            const profile_data = get_human_profile_data(fields_user_pills);

            const url = "/json/users/" + encodeURIComponent(user_id);
            const data = {
                full_name: JSON.stringify(full_name.val()),
                is_admin: JSON.stringify(user_role_select_value === 'admin'),
                is_guest: JSON.stringify(user_role_select_value === 'guest'),
                profile_data: JSON.stringify(profile_data),
            };

            settings_ui.do_settings_change(channel.patch, url, data, status_field);
            overlays.close_modal('#admin-human-form');
        });
    });
}

function handle_bot_form(tbody, status_field) {
    tbody.on("click", ".open-user-form", function (e) {
        const user_id = parseInt($(e.currentTarget).attr("data-user-id"), 10);
        const bot = people.get_by_user_id(user_id);

        if (!bot) {
            return;
        }

        const modal = open_bot_form(bot);

        modal.find('.submit_bot_change').on("click", function (e) {
            e.preventDefault();
            e.stopPropagation();

            const full_name = modal.find("input[name='full_name']");

            const url = "/json/bots/" + encodeURIComponent(user_id);
            const data = {
                full_name: full_name.val(),
            };

            const owner_select_value = modal.find('.bot_owner_select').val();
            if (owner_select_value) {
                data.bot_owner_id = people.get_by_email(owner_select_value).user_id;
            }

            settings_ui.do_settings_change(channel.patch, url, data, status_field);
            overlays.close_modal('#admin-bot-form');
        });
    });
}

exports.on_load_success = function (realm_people_data) {
    meta.loaded = true;

    populate_users(realm_people_data);
};

section.active.handle_events = () => {
    const tbody = $('#admin_users_table').expectOne();
    const status_field = $('#user-field-status').expectOne();

    handle_deactivation(tbody, status_field);
    handle_reactivation(tbody, status_field);
    handle_human_form(tbody, status_field);
};

section.deactivated.handle_events = () => {
    const tbody = $('#admin_deactivated_users_table').expectOne();
    const status_field = $("#deactivated-user-field-status").expectOne();

    handle_deactivation(tbody, status_field);
    handle_reactivation(tbody, status_field);
    handle_human_form(tbody, status_field);
};

section.bots.handle_events = () => {
    const tbody = $('#admin_bots_table').expectOne();
    const status_field = $("#bot-field-status").expectOne();

    handle_bot_owner_profile(tbody);
    handle_bot_deactivation(tbody, status_field);
    handle_reactivation(tbody, status_field);
    handle_bot_form(tbody, status_field);
};

exports.set_up = function () {
    start_data_load();
    section.active.handle_events();
    section.deactivated.handle_events();
    section.bots.handle_events();
};

window.settings_users = exports;
