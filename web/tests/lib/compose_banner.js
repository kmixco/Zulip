"use strict";

const compose_banner = require("../../src/compose_banner");

const $ = require("./zjquery");

exports.mock_banners = () => {
    // zjquery doesn't support `remove`, which is used when clearing the compose box.
    // TODO: improve how we test this so that we don't have to mock things like this.
    for (const classname of Object.values(compose_banner.CLASSNAMES)) {
        $(`#compose_banners .${classname.replaceAll(" ", ".")}`).remove = () => {};
    }
    $("#compose_banners .warning").remove = () => {};
    $("#compose_banners .error").remove = () => {};
};
