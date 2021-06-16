"use strict";

const Module = require("module");
const path = require("path");

const callsites = require("callsites");

const $ = require("../zjsunit/zjquery");

const new_globals = new Set();
let old_globals = {};

let actual_load;
const module_mocks = new Map();
const used_module_mocks = new Set();

const jquery_path = require.resolve("jquery");
const real_jquery_path = require.resolve("../zjsunit/real_jquery.js");

let in_mid_render = false;
let jquery_function;

function load(request, parent, isMain) {
    const filename = Module._resolveFilename(request, parent, isMain);
    if (module_mocks.has(filename)) {
        used_module_mocks.add(filename);
        const obj = module_mocks.get(filename);

        // Normal mocks are just objects.
        if (!obj.__template_fn) {
            return obj;
        }

        const actual_render = actual_load(request, parent, isMain);

        // For template mocks, we have an underlying object that
        // we wrap with a render function.
        const render = (...args) => {
            if (in_mid_render) {
                return actual_render(...args);
            }

            if (obj.f.__default) {
                throw new Error(`
                    You did render_foo = mock_template("${obj.__template_fn}")
                    but you also need to do override(render_foo, "f", () => {...}
                `);
            }

            const data = args[0];

            if (obj.exercise_template) {
                in_mid_render = true;
                const html = actual_render(...args);
                in_mid_render = false;

                // User will override "f" for now, which is a bit hacky.
                return obj.f(data, html);
            }

            return obj.f(data);
        };

        return render;
    }

    if (filename === jquery_path && parent.filename !== real_jquery_path) {
        return jquery_function || $;
    }

    return actual_load(request, parent, isMain);
}

exports.start = () => {
    if (actual_load !== undefined) {
        throw new Error("namespace.start was called twice in a row.");
    }
    actual_load = Module._load;
    Module._load = load;
};

// We provide `mock_cjs` for mocking a CommonJS module, and `mock_esm` for
// mocking an ES6 module.
//
// A CommonJS module:
// - loads other modules using `require()`,
// - assigns its public contents to the `exports` object or `module.exports`,
// - consists of a single JavaScript value, typically an object or function,
// - when imported by an ES6 module:
//   * is shallow-copied to a collection of immutable bindings, if it's an
//     object,
//   * is converted to a single default binding, if not.
//
// An ES6 module:
// - loads other modules using `import`,
// - declares its public contents using `export` statements,
// - consists of a collection of live bindings that may be mutated from inside
//   but not outside the module,
// - may have a default binding (that's just syntactic sugar for a binding
//   named `default`),
// - when required by a CommonJS module, always appears as an object.
//
// Most of our own modules are ES6 modules.
//
// For a third party module available in both formats that might present two
// incompatible APIs (especially if the CommonJS module is a function),
// Webpack will prefer the ES6 module if its availability is indicated by the
// "module" field of package.json, while Node.js will not; we need to mock the
// format preferred by Webpack.

function get_validated_filename(fn) {
    const filename = Module._resolveFilename(
        fn,
        require.cache[callsites()[1].getFileName()],
        false,
    );

    if (module_mocks.has(filename)) {
        throw new Error(`You already set up a mock for ${filename}`);
    }

    if (filename in require.cache) {
        throw new Error(`It is too late to mock ${filename}; call this earlier.`);
    }

    return filename;
}

exports.mock_cjs = (fn, obj) => {
    if (fn === "jquery") {
        throw new Error(
            "We automatically mock jquery to zjquery. Grep for mock_jquery if you want more control.",
        );
    }
    const filename = get_validated_filename(fn);
    module_mocks.set(filename, obj);

    return obj;
};

exports.mock_jquery = ($) => {
    jquery_function = $;
    return $;
};

exports.mock_template = (fn, exercise_template) => {
    // We create an object with an f() function that the test author
    // can override.
    const obj = {
        f: () => {},
        __template_fn: fn,
        exercise_template: Boolean(exercise_template),
    };

    obj.f.__default = true;

    const filename = get_validated_filename("../../static/templates/" + fn);

    // We update module_mocks with our object, but load() will return
    // its own function that calls our obj.f.
    module_mocks.set(filename, obj);

    return obj;
};

exports.mock_esm = (fn, obj = {}) => {
    if (typeof obj !== "object") {
        throw new TypeError("An ES module must be mocked with an object");
    }
    return exports.mock_cjs(fn, {...obj, __esModule: true});
};

exports.unmock_module = (request) => {
    const filename = Module._resolveFilename(
        request,
        require.cache[callsites()[1].getFileName()],
        false,
    );

    if (!module_mocks.has(filename)) {
        throw new Error(`Cannot unmock ${filename}, which was not mocked`);
    }

    if (!used_module_mocks.has(filename)) {
        throw new Error(`You asked to mock ${filename} but we never saw it during compilation.`);
    }

    module_mocks.delete(filename);
    used_module_mocks.delete(filename);
};

exports.set_global = function (name, val) {
    if (val === null) {
        throw new Error(`
            We try to avoid using null in our codebase.
        `);
    }

    if (!(name in old_globals)) {
        if (!(name in global)) {
            new_globals.add(name);
        }
        old_globals[name] = global[name];
    }
    global[name] = val;
    return val;
};

exports.zrequire = function (short_fn) {
    if (short_fn === "templates") {
        throw new Error(`
            There is no need to zrequire templates.js.

            The test runner automatically registers the
            Handlebar extensions.
        `);
    }

    return require(`../../static/js/${short_fn}`);
};

const staticPath = path.resolve(__dirname, "../../static") + path.sep;

exports.complain_about_unused_mocks = function () {
    for (const filename of module_mocks.keys()) {
        if (!used_module_mocks.has(filename)) {
            console.error(`You asked to mock ${filename} but we never saw it during compilation.`);
        }
    }
};

exports.finish = function () {
    /*
        Handle cleanup tasks after we've run one module.

        Note that we currently do lazy compilation of modules,
        so we need to wait till the module tests finish
        running to do things like detecting pointless mocks
        and resetting our _load hook.
    */
    jquery_function = undefined;

    if (actual_load === undefined) {
        throw new Error("namespace.finish was called without namespace.start.");
    }
    Module._load = actual_load;
    actual_load = undefined;

    module_mocks.clear();
    used_module_mocks.clear();

    for (const path of Object.keys(require.cache)) {
        if (path.startsWith(staticPath)) {
            delete require.cache[path];
        }
    }
    Object.assign(global, old_globals);
    old_globals = {};
    for (const name of new_globals) {
        delete global[name];
    }
    new_globals.clear();
};

exports.with_field = function (obj, field, val, f) {
    if ("__esModule" in obj && "__Rewire__" in obj) {
        const old_val = field in obj ? obj[field] : obj.__GetDependency__(field);
        try {
            obj.__Rewire__(field, val);
            return f();
        } finally {
            obj.__Rewire__(field, old_val);
        }
    } else {
        const had_val = Object.prototype.hasOwnProperty.call(obj, field);
        const old_val = obj[field];
        try {
            obj[field] = val;
            return f();
        } finally {
            if (had_val) {
                obj[field] = old_val;
            } else {
                delete obj[field];
            }
        }
    }
};

exports.with_overrides = function (test_function) {
    // This function calls test_function() and passes in
    // a way to override the namespace temporarily.

    const restore_callbacks = [];
    const unused_funcs = new Map();
    const override = function (obj, func_name, f) {
        // Given an object `obj` (which is usually a module object),
        // we re-map `obj[func_name]` to the `f` passed in by the caller.
        // Then the outer function here (`with_overrides`) automatically
        // restores the original value of `obj[func_name]` as its last
        // step.  Generally our code calls `run_test`, which wraps
        // `with_overrides`.
        if (typeof f !== "function") {
            throw new TypeError(
                "You can only override with a function. Use with_field for non-functions.",
            );
        }

        if (typeof obj !== "object" && typeof obj !== "function") {
            throw new TypeError(`We cannot override a function for ${typeof obj} objects`);
        }

        if (obj[func_name] !== undefined && typeof obj[func_name] !== "function") {
            throw new TypeError(`
                You are overriding a non-function with a function.
                This is almost certainly an error.
            `);
        }

        if (!unused_funcs.has(obj)) {
            unused_funcs.set(obj, new Map());
        }

        unused_funcs.get(obj).set(func_name, true);

        const old_f =
            "__esModule" in obj && "__Rewire__" in obj && !(func_name in obj)
                ? obj.__GetDependency__(func_name)
                : obj[func_name];

        const new_f = function (...args) {
            unused_funcs.get(obj).delete(func_name);
            return f.apply(this, args);
        };

        // Let zjquery know this function was patched with override,
        // so it doesn't complain about us modifying it.  (Other
        // code can also use this, as needed.)
        new_f._patched_with_override = true;

        if ("__esModule" in obj && "__Rewire__" in obj) {
            obj.__Rewire__(func_name, new_f);
            restore_callbacks.push(() => {
                obj.__Rewire__(func_name, old_f);
            });
        } else {
            obj[func_name] = new_f;
            restore_callbacks.push(() => {
                obj[func_name] = old_f;
            });
        }
    };

    try {
        test_function(override);
    } finally {
        restore_callbacks.reverse();
        for (const restore_callback of restore_callbacks) {
            restore_callback();
        }
    }

    for (const [obj, module_unused_funcs] of unused_funcs.entries()) {
        for (const unused_name of module_unused_funcs.keys()) {
            if (obj.__template_fn) {
                throw new Error(`The ${obj.__template_fn} template was never rendered.`);
            } else {
                throw new Error(unused_name + " never got invoked!");
            }
        }
    }
};
