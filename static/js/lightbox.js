var lightbox = (function () {
var exports = {};

var images = [];
var is_open = false;

var get_image_title = function (image) {
    var image_title = $(image).attr("title");
    if (image_title) {
        return image_title;
    }
    return $(image).parent().attr("title");
};

function display_image(image, user) {
    if (!is_open) {
        images = Array.prototype.slice.call($(".focused_table .messagebox-content img"));
        var $image_list = $("#lightbox_overlay .image-list").html("");

        images.forEach(function (img) {
            var src = img.getAttribute("src");
            var className = $(image).attr("src").match(src) ? "image selected" : "image";

            var node = $("<div></div>", {
                class: className,
                title: get_image_title(img),
                "data-zid": $(img).closest(".message_row").attr("zid"),
                "data-src": src,
            }).css({ backgroundImage: "url(" + src + ")"});

            $image_list.append(node);
        }, "");
    }

    // image should be an Image Object in JavaScript.
    var url = $(image).attr("src");
    var title = get_image_title(image);

    $("#lightbox_overlay .player-container").hide();
    $("#lightbox_overlay .image-actions, .image-description, .download").show();

    var img = new Image();
    img.src = url;
    $("#lightbox_overlay .image-preview").html("").show()
        .append(img);

    $(".image-description .title").text(title || "N/A");
    $(".image-description .user").text(user);

    $(".image-actions .open, .image-actions .download").attr("href", url);
}

function display_youtube_video(id) {
    $("#lightbox_overlay .image-preview, .image-description, .download").hide();

    var iframe = document.createElement("iframe");
    iframe.width = window.innerWidth;
    iframe.height = window.innerWidth * 0.5625;
    iframe.src = "https://www.youtube.com/embed/" + id;
    iframe.setAttribute("frameborder", 0);
    iframe.setAttribute("allowfullscreen", true);

    $("#lightbox_overlay .player-container").html("").show().append(iframe);
    $(".image-actions .open").attr("href", "https://youtu.be/" + id);
}

exports.open = function (data) {
    switch (data.type) {
        case "photo":
            display_image(data.image, data.user);
            is_open = true;
            break;
        case "youtube":
            display_youtube_video(data.id);
            is_open = true;
            break;
        default:
            break;
    }

    $("#lightbox_overlay").addClass("show");
    popovers.hide_all();
    lightbox.is_open = true;
};

exports.show_from_selected_message = function () {
    var selected_msg = $(".selected_message").find("img");
    if (selected_msg.length !== 0) {
      exports.show_from_inline_image(selected_msg);
    }
};

exports.show_from_inline_image = function ($img) {
    var zid = rows.id($img.closest(".message_row"));
    var user = message_store.get(zid).sender_full_name;
    if ($img.parent().parent().hasClass("youtube-video")) {
        lightbox.open({
            type: "youtube",
            id: $img.data("id"),
        });
    } else {
        lightbox.open({
            type: "photo",
            image: $img[0],
            user: user,
        });
    }
};

exports.prev = function () {
    $(".image-list .image.selected").prev().click();
};

exports.next = function () {
    $(".image-list .image.selected").next().click();
};

Object.defineProperty(exports, "is_open", {
    get: function () {
        return is_open;
    },
    set: function (value) {
        if (typeof value === "boolean") {
            is_open = value;
        }
    },
});

return exports;
}());

if (typeof module !== 'undefined') {
    module.exports = lightbox;
}
