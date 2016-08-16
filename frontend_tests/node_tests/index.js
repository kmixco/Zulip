global.assert = require('assert');
var fs = require('fs');
var path = require('path');
var Handlebars = require('handlebars');
require('third/string-prototype-codepointat/codepointat.js');

global.Dict = require('js/dict');
global._ = require('third/underscore/underscore.js');
var _ = global._;

// Run all the JS scripts in our test directory.  Tests do NOT run
// in isolation.

var oneFileFilter = [];
var testsDifference = [];
if (process.argv[2] ) {
    oneFileFilter = process.argv
      .slice(2)
      .map(function (filename) {return filename.replace(/\.js$/i, '');});
}

var tests = fs.readdirSync(__dirname)
  .filter(function (filename) {return (/\.js$/i).test(filename);})
  .map(function (filename) {return filename.replace(/\.js$/i, '');});

if (oneFileFilter.length > 0) {
    tests = tests.filter(function (filename) {
        return oneFileFilter.indexOf(filename) !== -1;
    });
    testsDifference = _.difference(oneFileFilter, tests);
}
tests.sort();


var dependencies = [];
var old_builtins = {};

global.set_global = function (name, val) {
    global[name] = val;
    dependencies.push(name);
    return val;
};

global.patch_builtin = function (name, val) {
    old_builtins[name] = global[name];
    global[name] = val;
    return val;
};

global.add_dependencies = function (dct) {
    _.each(dct, function (fn, name) {
        var obj = require(fn);
        set_global(name, obj);
    });
};

function template_dir() {
    return __dirname + '/../../static/templates/';
}

global.make_sure_all_templates_have_been_compiled = function () {
    var dir = template_dir();
    var fns = fs.readdirSync(dir).filter(function (fn) {
        return (/\.handlebars/).test(fn);
    });

    _.each(fns, function (fn) {
        var name = fn.split('.')[0];
        if (!Handlebars.templates[name]) {
            throw "The file " + fn + " has no test coverage.";
        }
    });
};

global.use_template = function (name) {
    if (Handlebars.templates === undefined) {
        Handlebars.templates = {};
    }
    var data = fs.readFileSync(template_dir() + name + '.handlebars').toString();
    Handlebars.templates[name] = Handlebars.compile(data);
};

var mkdir_p = function (path) {
    // This works like mkdir -p in Unix.
    try {
        fs.mkdirSync(path);
    } catch(e) {
        if ( e.code !== 'EEXIST' ) {
            throw e;
        }
    }
    return path;
};

var output_dir = (function () {
    mkdir_p('var');
    var dir = mkdir_p('var/test-js-with-node');
    return dir;
}());

var output_fn = path.join(output_dir, 'output.html');

(function () {
    var data = '';

    data += '<link href="../../static/styles/zulip.css" rel="stylesheet">\n';
    data += '<link href="../../static/styles/thirdparty-fonts.css" rel="stylesheet">\n';
    data += '<link href="../../static/third/bootstrap/css/bootstrap.css" rel="stylesheet">\n';
    data += '<style type="text/css">.collapse {height: inherit}</style>\n';
    data += '<style type="text/css">body {width: 500px; margin: auto; overflow: scroll}</style>\n';
    data += '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">';
    data += '<h1>Output of node unit tests</h1>\n';
    fs.writeFileSync(output_fn, data);
}());

global.write_test_output = function (label, output) {
    var data = '';

    data += '<hr>';
    data += '<h3>' + label + '</h3>';
    data += output;
    data += '\n';
    fs.appendFileSync(output_fn, data);
};

global.write_handlebars_output = function (label, output) {
    global.write_test_output(label + '.handlebars', output);
};

global.append_test_output = function (output) {
    fs.appendFileSync(output_fn, output);
};

tests.forEach(function (filename) {
    if (filename === 'index') {
        return;
    }
    console.info('running tests for ' + filename);
    require('./' + filename);

    dependencies.forEach(function (name) {
        delete global[name];
    });
    dependencies = [];
    _.extend(global, old_builtins);
    old_builtins = {};
});

if (oneFileFilter.length > 0 && testsDifference.length > 0) {
    testsDifference.forEach(function (filename) {
        console.log(filename + " does not exist");
    });
    if (oneFileFilter.length > testsDifference.length) {
        console.info("To see more output, open " + output_fn);
    }
} else {
    console.info("To see more output, open " + output_fn);
}
