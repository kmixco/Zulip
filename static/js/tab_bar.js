const render_tab_bar = require('../templates/tab_bar.hbs');

function get_sub_count(current_stream) {
    const sub_count = current_stream.subscriber_count;
    return sub_count;
}

function get_formatted_sub_count(current_stream) {
    let sub_count = get_sub_count(current_stream);
    if (sub_count >= 1000) {
        // parseInt() is used to floor the value of division to an integer
        sub_count = parseInt(sub_count / 1000, 10) + "k";
    }
    return sub_count;
}

function make_tab_data(filter) {
    const tab_data = {};
    if (filter === undefined) {
        return {
            title: 'All messages',
            icon: 'home',
        };
    }
    tab_data.title = filter.get_title();
    tab_data.icon = filter.get_icon();
    if (tab_data.icon === 'hashtag' || tab_data.icon === 'lock') {
        const stream = filter.operands("stream")[0];
        const current_stream  = stream_data.get_sub_by_name(stream);
        if (current_stream) {
            tab_data.rendered_narrow_description = current_stream.rendered_description;
            tab_data.sub_count = get_sub_count(current_stream);
            tab_data.formatted_sub_count = get_formatted_sub_count(current_stream);
            tab_data.stream_settings_link = "#streams/" + current_stream.stream_id + "/" + current_stream.name;
        } else {
            tab_data.title = 'Unknown Stream';
            tab_data.sub_count = '0';
            tab_data.formatted_sub_count = '0';
            tab_data.rendered_narrow_description = "This stream does not exist or is private.";
        }
    }
    return tab_data;
}

exports.colorize_tab_bar = function () {
    const filter = narrow_state.filter();
    if (filter === undefined || !filter.has_operator('stream')) {return;}
    const color_for_stream = stream_data.get_color(filter.operands("stream")[0]);
    const stream_light = colorspace.getHexColor(colorspace.getDecimalColor(color_for_stream));
    $("#tab_list .fa-hashtag").css('color', stream_light);
    $("#tab_list .fa-lock").css('color', stream_light);
};

function display_tab_bar(tab_bar_data) {
    const tab_bar = $("#tab_bar");
    tab_bar.empty();
    const rendered = render_tab_bar(tab_bar_data);
    tab_bar.append(rendered);
    if (tab_bar_data.stream_settings_link) {
        exports.colorize_tab_bar();
    }
    tab_bar.removeClass('notdisplayed');
}

function build_tab_bar(filter) {
    // This makes sure we don't waste time appending tab_bar on a template where it's never used
    if (filter && !filter.is_common_narrow()) {
        exports.open_search_bar_and_close_narrow_description();
    } else {
        const tab_bar_data = make_tab_data(filter);
        display_tab_bar(tab_bar_data);
        $(".search_closed").on("click", function (e) {
            exports.open_search_bar_and_close_narrow_description();
            $('#search_query').select();
            e.preventDefault();
            e.stopPropagation();
        });
        exports.close_search_bar_and_open_narrow_description();
    }
}

exports.exit_search = function () {
    const filter = narrow_state.filter();
    if (!filter || filter.is_common_narrow()) {
        // for common narrows, we change the UI (and don't redirect)
        exports.close_search_bar_and_open_narrow_description();
    } else {
        // for "searching narrows", we redirect
        window.location.replace(filter.generate_redirect_url());
    }
};

exports.update_stream_name = function (new_name) {
    const stream_name = $(".stream");
    if (stream_name !== undefined) {
        stream_name.text(new_name);
    }
};

exports.update_stream_description = function (rendered_new_description) {
    const stream_description = $(".narrow_description");
    if (stream_description !== undefined) {
        stream_description.html(rendered_new_description);
    }
};

exports.initialize = function () {
    const filter = narrow_state.filter();
    build_tab_bar(filter);

    // register navbar click handlers
    $('#search_exit').on("click", function (e) {
        tab_bar.exit_search();
        e.preventDefault();
        e.stopPropagation();
    });

    $(".search_open").on("click", function (e) {
        $('#search_query').typeahead('lookup').focus();
        e.preventDefault();
        e.stopPropagation();
    });
};

exports.open_search_bar_and_close_narrow_description = function () {
    $(".navbar-search").addClass("expanded");
    $("#tab_list").addClass("hidden");
};

exports.close_search_bar_and_open_narrow_description = function () {
    $(".navbar-search").removeClass("expanded");
    $("#tab_list").removeClass("hidden");
};

window.tab_bar = exports;
