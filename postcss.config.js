"use strict";

const path = require("path");

const {media_breakpoints} = require("./static/js/css_variables");

module.exports = ({file}) => ({
    plugins: [
        (file.basename ?? path.basename(file)) === "night_mode.css" &&
            // Add postcss-import plugin with postcss-prefixwrap to handle
            // the flatpickr dark theme. We do this because flatpickr themes
            // are not scoped. See https://github.com/flatpickr/flatpickr/issues/2168.
            require("postcss-import")({
                plugins: [require("postcss-prefixwrap")("%night-mode-block")],
            }),
        require("postcss-nested"),
        require("postcss-extend-rule"),
        require("postcss-mixins"),
        require("postcss-simple-vars")({variables: media_breakpoints}),
        require("postcss-calc"),
        require("postcss-media-minmax"),
        require("autoprefixer"),
    ],
});
