var input_pill = (function () {

var exports = {};

exports.random_id = function () {
    return Math.random().toString(16);
};

exports.create = function (opts) {
    // a dictionary of the key codes that are associated with each key
    // to make if/else more human readable.
    var KEY = {
        ENTER: 13,
        BACKSPACE: 8,
        LEFT_ARROW: 37,
        RIGHT_ARROW: 39,
        COMMA: 188,
    };

    if (!opts.container) {
        blueslip.error('Pill needs container.');
        return;
    }

    if (!opts.create_item_from_text) {
        blueslip.error('Pill needs create_item_from_text');
        return;
    }

    if (!opts.get_text_from_item) {
        blueslip.error('Pill needs get_text_from_item');
        return;
    }

    // a stateful object of this `pill_container` instance.
    // all unique instance information is stored in here.
    var store = {
        pills: [],
        $parent: opts.container,
        $input: opts.container.find(".input"),
        create_item_from_text: opts.create_item_from_text,
        get_text_from_item: opts.get_text_from_item,
    };

    // a dictionary of internal functions. Some of these are exposed as well,
    // and nothing in here should be assumed to be private (due to the passing)
    // of the `this` arg in the `Function.prototype.bind` use in the prototype.
    var funcs = {
        // return the value of the contenteditable input form.
        value: function (input_elem) {
            return input_elem.innerText.trim();
        },

        // clear the value of the input form.
        clear: function (input_elem) {
            input_elem.innerText = "";
        },

        clear_text: function () {
            store.$input.text("");
        },

        create_item: function (text) {
            var existing_items = funcs.items();
            var item = store.create_item_from_text(text, existing_items);

            if (!item || !item.display_value) {
                store.$input.addClass("shake");
                return;
            }

            if (typeof store.onPillCreate === "function") {
                store.onPillCreate();
            }

            return item;
        },

        // This is generally called by typeahead logic, where we have all
        // the data we need (as opposed to, say, just a user-typed email).
        appendValidatedData: function (item) {
            var id = exports.random_id();

            if (!item.display_value) {
                blueslip.error('no display_value returned');
                return;
            }

            var payload = {
                id: id,
                item: item,
            };

            store.pills.push(payload);

            payload.$element = $("<div class='pill' data-id='" + payload.id + "' tabindex=0>" + item.display_value + "<div class='exit'>&times;</div></div>");
            store.$input.before(payload.$element);
        },

        // this appends a pill to the end of the container but before the
        // input block.
        appendPill: function (value) {
            if (value.length === 0) {
              return;
            }
            if (value.match(",")) {
                funcs.insertManyPills(value);
                return false;
            }

            var payload = this.create_item(value);
            // if the pill object is undefined, then it means the pill was
            // rejected so we should return out of this.
            if (!payload) {
                return false;
            }

            this.appendValidatedData(payload);
        },

        // this searches given a particlar pill ID for it, removes the node
        // from the DOM, removes it from the array and returns it.
        // this would generally be used for DOM-provoked actions, such as a user
        // clicking on a pill to remove it.
        removePill: function (id) {
            var idx;
            for (var x = 0; x < store.pills.length; x += 1) {
                if (store.pills[x].id === id) {
                    idx = x;
                }
            }

            if (typeof idx === "number") {
                store.pills[idx].$element.remove();
                var pill = store.pills.splice(idx, 1);
                if (typeof store.removePillFunction === "function") {
                    store.removePillFunction(pill);
                }

                return pill;
            }
        },

        // this will remove the last pill in the container -- by defaulat tied
        // to the "backspace" key when the value of the input is empty.
        removeLastPill: function () {
            var pill = store.pills.pop();

            if (pill) {
                pill.$element.remove();
                if (typeof store.removePillFunction === "function") {
                    store.removePillFunction(pill);
                }
            }
        },

        removeAllPills: function () {
            while (store.pills.length > 0) {
                this.removeLastPill();
            }

            this.clear(store.$input[0]);
        },

        insertManyPills: function (pills) {
            if (typeof pills === "string") {
                pills = pills.split(/,/g).map(function (pill) {
                    return pill.trim();
                });
            }

            // this is an array to push all the errored values to, so it's drafts
            // of pills for the user to fix.
            var drafts = [];

            pills.forEach(function (pill) {
                // if this returns `false`, it erroed and we should push it to
                // the draft pills.
                if (funcs.appendPill(pill) === false) {
                    drafts.push(pill);
                }
            });

            store.$input.text(drafts.join(", "));
            // when using the `text` insertion feature with jQuery the caret is
            // placed at the beginning of the input field, so this moves it to
            // the end.
            ui_util.place_caret_at_end(store.$input[0]);

            // this sends a flag that the operation wasn't completely successful,
            // which in this case is defined as some of the pills not autofilling
            // correclty.
            if (drafts.length > 0) {
                return false;
            }
        },

        getByID: function (id) {
            return _.find(store.pills, function (pill) {
                return pill.id === id;
            });
        },

        items: function () {
            return _.pluck(store.pills, 'item');
        },
    };

    (function events() {
        store.$parent.on("keydown", ".input", function (e) {
            var char = e.keyCode || e.charCode;

            if (char === KEY.ENTER) {
                // regardless of the value of the input, the ENTER keyword
                // should be ignored in favor of keeping content to one line
                // always.
                e.preventDefault();

                // if there is input, grab the input, make a pill from it,
                // and append the pill, then clear the input.
                if (funcs.value(e.target).length > 0) {
                    var value = funcs.value(e.target);

                    // append the pill and by proxy create the pill object.
                    var ret = funcs.appendPill(value);

                    // if the pill to append was rejected, no need to clear the
                    // input; it may have just been a typo or something close but
                    // incorrect.
                    if (ret !== false) {
                        // clear the input.
                        funcs.clear(e.target);
                        e.stopPropagation();
                    }
                }

                return;
            }

            // if the user backspaces and there is input, just do normal char
            // deletion, otherwise delete the last pill in the sequence.
            if (char === KEY.BACKSPACE && funcs.value(e.target).length === 0) {
                e.preventDefault();
                funcs.removeLastPill();

                return;
            }

            // if one is on the ".input" element and back/left arrows, then it
            // should switch to focus the last pill in the list.
            // the rest of the events then will be taken care of in the function
            // below that handles events on the ".pill" class.
            if (char === KEY.LEFT_ARROW) {
                if (window.getSelection().anchorOffset === 0) {
                    store.$parent.find(".pill").last().focus();
                }
            }

            // users should not be able to type a comma if the last field doesn't
            // validate.
            if (char === KEY.COMMA) {
                // if the pill is successful, it will create the pill and clear
                // the input.
                if (funcs.appendPill(store.$input.text().trim()) !== false) {
                    funcs.clear(store.$input[0]);
                // otherwise it will prevent the typing of the comma because they
                // cannot add another pill until this input is valid.
                } else {
                    e.preventDefault();
                    return;
                }
            }
        });

        // handle events while hovering on ".pill" elements.
        // the three primary events are next, previous, and delete.
        store.$parent.on("keydown", ".pill", function (e) {
            var char = e.keyCode || e.charCode;

            var $pill = store.$parent.find(".pill:focus");

            if (char === KEY.LEFT_ARROW) {
                $pill.prev().focus();
            } else if (char === KEY.RIGHT_ARROW) {
                $pill.next().focus();
            } else if (char === KEY.BACKSPACE) {
                var $next = $pill.next();
                var id = $pill.data("id");
                funcs.removePill(id);
                $next.focus();
                // the "backspace" key in FireFox will go back a page if you do
                // not prevent it.
                e.preventDefault();
            }
        });

        // when the shake animation is applied to the ".input" on invalid input,
        // we want to remove the class when finished automatically.
        store.$parent.on("animationend", ".input", function () {
            $(this).removeClass("shake");
        });

        // replace formatted input with plaintext to allow for sane copy-paste
        // actions.
        store.$parent.on("paste", ".input", function (e) {
            e.preventDefault();

            // get text representation of clipboard
            var text = (e.originalEvent || e).clipboardData.getData('text/plain');

            // insert text manually
            document.execCommand("insertHTML", false, text);

            funcs.insertManyPills(store.$input.text().trim());
        });

        // when the "×" is clicked on a pill, it should delete that pill and then
        // select the next pill (or input).
        store.$parent.on("click", ".exit", function () {
            var $pill = $(this).closest(".pill");
            var $next = $pill.next();
            var id = $pill.data("id");

            funcs.removePill(id);
            $next.focus();
        });

        store.$parent.on("click", function (e) {
            if ($(e.target).is(".pill-container")) {
                $(this).find(".input").focus();
            }
        });

        store.$parent.on("copy", ".pill", function (e) {
            var id = store.$parent.find(":focus").data("id");
            var data = funcs.getByID(id);
            e.originalEvent.clipboardData.setData("text/plain", store.get_text_from_item(data.item));
            e.preventDefault();
        });
    }());

    // the external, user-accessible prototype.
    var prototype = {
        appendValue: funcs.appendPill.bind(funcs),
        appendValidatedData: funcs.appendValidatedData.bind(funcs),

        items: funcs.items,

        onPillCreate: function (callback) {
            store.onPillCreate = callback;
        },

        onPillRemove: function (callback) {
            store.removePillFunction = callback;
        },

        clear: funcs.removeAllPills.bind(funcs),
        clear_text: funcs.clear_text,
    };

    return prototype;
};

return exports;

}());

if (typeof module !== 'undefined') {
    module.exports = input_pill;
}
