exports.default_color = "#c2c2c2";

exports.presets = {
    color: ["a47462", "c2726a", "e4523d", "e7664d", "ee7e4a", "f4ae55",
            "76ce90", "53a063", "94c849", "bfd56f", "fae589", "f5ce6e",
            "a6dcbf", "addfe5", "a6c7e5", "4f8de4", "95a5fd", "b0a5fd",
            "c2c2c2", "c8bebf", "c6a8ad", "e79ab5", "bd86e5", "9987e1"],
};

// Classes which could be returned by get_color_class.
exports.color_classes = "dark_background";

function update_table_stream_color(table, stream_name, color) {
    // This is ugly, but temporary, as the new design will make it
    // so that we only have color in the headers.
    const style = color;
    const color_class = exports.get_color_class(color);

    const stream_labels = $("#floating_recipient_bar").add(table).find(".stream_label");

    for (const label of stream_labels) {
        const $label = $(label);
        if ($label.text().trim() === stream_name) {
            const messages = $label.closest(".recipient_row").children(".message_row");
            messages
                .children(".messagebox")
                .css(
                    "box-shadow",
                    "inset 2px 0px 0px 0px " + style + ", -1px 0px 0px 0px " + style,
                );
            messages
                .children(".date_row")
                .css(
                    "box-shadow",
                    "inset 2px 0px 0px 0px " + style + ", -1px 0px 0px 0px " + style,
                );
            $label.css({background: style, "border-left-color": style});
            $label.removeClass(exports.color_classes);
            $label.addClass(color_class);
        }
    }
}

function update_stream_sidebar_swatch_color(id, color) {
    $("#stream_sidebar_swatch_" + id).css("background-color", color);
    $("#stream_sidebar_privacy_swatch_" + id).css("color", color);
}

function update_historical_message_color(stream_name, color) {
    update_table_stream_color($(".focused_table"), stream_name, color);
    if ($(".focused_table").attr("id") !== "#zhome") {
        update_table_stream_color($("#zhome"), stream_name, color);
    }
}

const hexDigits = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f"];

function hex(x) {
    return isNaN(x) ? "00" : hexDigits[(x - x % 16) / 16] + hexDigits[x % 16];
}

// Function to convert rgb color to hex format
function rgb2hex(rgb) {
    rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
    return "#" + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
}

exports.update_stream_color = function (sub, color, opts) {
    opts = {update_historical: false, ...opts};
    sub.color = color;
    const stream_id = sub.stream_id;
    // The swatch in the subscription row header.
    $(".stream-row[data-stream-id='" + stream_id + "'] .icon").css('background-color', color);
    $("#subscription_overlay .subscription_settings[data-stream-id='" + stream_id + "'] .large-icon").css("color", color);

    if (opts.update_historical) {
        update_historical_message_color(sub.name, color);
    }
    update_stream_sidebar_swatch_color(stream_id, color);
    tab_bar.colorize_tab_bar();
};

$("body").on("change", "#stream_color_picker", (e) => {
    const color = e.target.value;
    const stream_id = parseInt(e.target.getAttribute("stream_id"), 10);
    subs.set_color(stream_id, color);
});

$("body").on("click", (e) => {
    if (e.target.matches("#custom_color")) {
        const color_picker = $("body").find("#stream_color_picker");
        $(color_picker).click();
    }

    if (e.target.matches("#color_picker") || e.target.matches("#color_swatch") || e.target.matches("#color_dropdown")) {
        $("body").find(".color_picker_body").toggleClass("visible");
    } else if (!(e.target.class === "color_picker_body" || $(e.target).parents(".color_picker_body").length)) {
        if ($("body").find(".color_picker_body").hasClass("visible")) {
            $("body").find(".color_picker_body").removeClass("visible");
        }
    }

    if (e.target.matches(".presets")) {
        const color = $(e.target).css("background-color");
        const stream_id = parseInt($(e.target).parent().attr("stream_id"), 10);
        subs.set_color(stream_id, rgb2hex(color));
    }
});

let lightness_threshold;
exports.initialize = function () {
    // sRGB color component for dark label text.
    // 0x33 to match the color #333333 set by Bootstrap.
    const label_color = 0x33;
    const lightness = colorspace.luminance_to_lightness(colorspace.sRGB_to_linear(label_color));

    // Compute midpoint lightness between that and white (100).
    lightness_threshold = (lightness + 100) / 2;
};

// From a background color (in format "#fff" or "#ffffff")
// pick a CSS class (or empty string) to determine the
// text label color etc.
//
// It would be better to work with an actual data structure
// rather than a hex string, but we have to deal with values
// already saved on the server, etc.
//
// This gets called on every message, so cache the results.
exports.get_color_class = _.memoize((color) => {
    let match;
    let i;
    const channel = [0, 0, 0];
    let mult = 1;

    match = /^#([\da-fA-F]{2})([\da-fA-F]{2})([\da-fA-F]{2})$/.exec(color);
    if (!match) {
        // 3-digit shorthand; Spectrum gives this e.g. for pure black.
        // Multiply each digit by 16+1.
        mult = 17;

        match = /^#([\da-fA-F])([\da-fA-F])([\da-fA-F])$/.exec(color);
        if (!match) {
            // Can't understand color.
            return "";
        }
    }

    // CSS colors are specified in the sRGB color space.
    // Convert to linear intensity values.
    for (i = 0; i < 3; i += 1) {
        channel[i] = colorspace.sRGB_to_linear(mult * parseInt(match[i + 1], 16));
    }

    // Compute perceived lightness as CIE L*.
    const lightness = colorspace.luminance_to_lightness(colorspace.rgb_luminance(channel));

    // Determine if we're past the midpoint between the
    // dark and light label lightness.
    return lightness < lightness_threshold ? "dark_background" : "";
});

window.stream_color = exports;
