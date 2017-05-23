var noop = function () {};

var zjquery = (function () {

var elems = {};
var exports = {};

function new_elem(selector) {
    var value;
    var shown = false;
    var self = {
        val: function () {
            if (arguments.length === 0) {
                return value || '';
            }
            value = arguments[0];
        },
        css: noop,
        data: noop,
        empty: noop,
        height: noop,
        removeAttr: noop,
        removeData: noop,
        trigger: noop,
        show: function () {
            shown = true;
        },
        hide: function () {
            shown = false;
        },
        addClass: function (class_name) {
            assert.equal(class_name, 'active');
            shown = true;
        },
        removeClass: function (class_name) {
            if (class_name === 'status_classes') {
                return self;
            }
            assert.equal(class_name, 'active');
            shown = false;
        },
        debug: function () {
            return {
                value: value,
                shown: shown,
                selector: selector,
            };
        },
        visible: function () {
            return shown;
        },
    };
    return self;
}

exports.zjquery = function (selector) {
    if (elems[selector] === undefined) {
        var elem = new_elem(selector);
        elems[selector] = elem;
    }
    return elems[selector];
};

exports.zjquery.trim = function (s) { return s; };

exports.zjquery.state = function () {
    // useful for debugging
    var res =  _.map(elems, function (v) {
        return v.debug();
    });

    res = _.map(res, function (v) {
        return [v.selector, v.value, v.shown];
    });

    res.sort();

    return res;
};

exports.zjquery.Event = noop;

return exports;
}());
module.exports = zjquery;
