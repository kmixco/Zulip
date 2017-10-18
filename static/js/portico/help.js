const Ps = require('perfect-scrollbar');

(function () {
    var html_map = {};
    var loading = {
        name: null,
    };
    var no_of_images = 0;
    var no_of_loaded_images = 0;
    function scroll_to_anchor_once_images_ready() {
        var imgs = document.images;
        no_of_loaded_images = 0;
        no_of_images = ( imgs && imgs.length ) || 0;
        if (( !imgs ) || no_of_images == 0 ) {
            scroll_to_anchor(window.location.href);
        }
        [].forEach.call( imgs, function( img ) {
            img.addEventListener( 'load', scroll_when_ready, false );
        } );
    }
    function scroll_when_ready() {
        no_of_loaded_images++;
        if ( no_of_loaded_images === no_of_images ) {
            scroll_to_anchor(window.location.href);
        }
    }
    
    var scroll_to_anchor = function(path) {
        var container = $(".markdown")[0];
        var path_split = path.split("#");
        if (path_split.length==2) {
            document.getElementById(path_split[1]).scrollIntoView();
            console.log(container.scrollTop);
        }
        else {
               container.scrollTop = 0;
        }
    }
    var fetch_page = function (path, callback) {
        $.get(path, function (res) {
            var $html = $(res).find(".markdown .content");
            $html.find(".back-to-home").remove();

            callback($html.html().trim());
        });
    };

    $(".sidebar h2").click(function (e) {
        var $next = $(e.target).next();

        if ($next.is("ul")) {
            $next.slideToggle("fast", "swing", function () {
                Ps.update($(".markdown")[0]);
            });
        }
    });

    $(".sidebar a").click(function (e) {
        var path = $(this).attr("href");
        var container = $(".markdown")[0];


        if (loading.name === path) {
            return;
        }

        history.pushState({}, "", path);

        if (html_map[path]) {
            $(".markdown .content").html(html_map[path]);
            scroll_to_anchor_once_images_ready();
            Ps.update(container);
        } else {
            loading.name = path;
            fetch_page(path, function (res) {
                html_map[path] = res;
                $(".markdown .content").html(html_map[path]);
                scroll_to_anchor_once_images_ready();
                loading.name = null;
                Ps.update(container);
            });
        }

        container.scrollTop = 0;
        $(".sidebar").removeClass("show");

        e.preventDefault();
    });

    Ps.initialize($(".markdown")[0], {
        suppressScrollX: true,
        useKeyboard: false,
        wheelSpeed: 0.68,
    });

    Ps.initialize($(".sidebar")[0], {
        suppressScrollX: true,
        useKeyboard: false,
        wheelSpeed: 0.68,
    });

    window.onresize = function () {
        Ps.update($(".markdown")[0]);
    };

    window.addEventListener("popstate", function () {
        var path = window.location.pathname;
        $(".markdown .content").html(html_map[path]);
    });

    $(".hamburger").click(function () {
        $(".sidebar").toggleClass("show");
    });

    $(".markdown").click(function () {
        if ($(".sidebar.show").length) {
            $(".sidebar.show").toggleClass("show");
        }
    });
}());
