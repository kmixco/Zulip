zrequire('scroll_util');
zrequire('list_render');

// We need these stubs to get by instanceof checks.
// The list_render library allows you to insert objects
// that are either jQuery, Element, or just raw HTML
// strings.  We initially test with raw strings.
set_global('jQuery', 'stub');
set_global('Element', function () {
    return { };
});

// We only need very simple jQuery wrappers for when the
// "real" code wraps html or sets up click handlers.
// We'll simulate most other objects ourselves.
set_global('$', (arg) => {
    if (arg.to_jquery) {
        return arg.to_jquery();
    }

    return {
        html: () => arg,
    };
});

function make_containers() {
    // We build objects here that simulate jQuery containers.
    // The main thing to do at first is simulate that our
    // parent container is the nearest ancestor to our main
    // container that has a max-height attribute, and then
    // the parent container will have a scroll event attached to
    // it.  This is a good time to read set_up_event_handlers
    // in the real code.
    const parent_container = {};
    const container = {};

    container.parent = () => parent_container;
    container.length = () => 1;
    container.is = () => false;
    container.css = (prop) => {
        assert.equal(prop, 'max-height');
        return 'none';
    };

    parent_container.is = () => false;
    parent_container.length = () => 1;
    parent_container.css = (prop) => {
        assert.equal(prop, 'max-height');
        return 100;
    };

    // Capture the scroll callback so we can call it in
    // our tests.
    parent_container.on = (sel, f) => {
        assert.equal(sel, 'scroll.list_widget_container');
        parent_container.call_scroll = () => {
            f.call(parent_container);
        };
    };

    // Make our append function just set a field we can
    // check in our tests.
    container.append = (data) => {
        container.appended_data = data;
    };

    return {
        container: container,
        parent_container: parent_container,
    };
}

function make_search_input() {
    const $element = {};

    // Allow ourselves to be wrapped by $(...) and
    // return ourselves.
    $element.to_jquery = () => $element;

    $element.on = (event_name, f) => {
        assert.equal(event_name, 'input.list_widget_filter');
        $element.simulate_input_event = () => {
            const elem = {
                value: $element.val(),
            };
            f.call(elem);
        };
    };

    return $element;
}

function div(item) {
    return '<div>' + item + '</div>';
}

run_test('scrolling', () => {
    const {container, parent_container} = make_containers();

    const items = [];

    for (let i = 0; i < 200; i += 1) {
        items.push('item ' + i);
    }

    const opts = {
        modifier: (item) => item,
    };

    container.html = (html) => { assert.equal(html, ''); };
    list_render.create(container, items, opts);

    assert.deepEqual(
        container.appended_data.html(),
        items.slice(0, 80).join('')
    );

    // Set up our fake geometry so it forces a scroll action.
    parent_container.scrollTop = 180;
    parent_container.clientHeight = 100;
    parent_container.scrollHeight = 260;

    // Scrolling gets the next two elements from the list into
    // our widget.
    parent_container.call_scroll();
    assert.deepEqual(
        container.appended_data.html(),
        items.slice(80, 100).join('')
    );
});

run_test('filtering', () => {
    const {container} = make_containers();

    const search_input = make_search_input();

    const list = [
        'apple',
        'banana',
        'carrot',
        'dog',
        'egg',
        'fence',
        'grape',
    ];
    let opts = {
        filter: {
            element: search_input,
            predicate: (item, value) => {
                return item.includes(value);
            },
        },
        modifier: (item) => div(item),
    };

    container.html = (html) => { assert.equal(html, ''); };
    let widget = list_render.create(container, list, opts);

    let expected_html =
        '<div>apple</div>' +
        '<div>banana</div>' +
        '<div>carrot</div>' +
        '<div>dog</div>' +
        '<div>egg</div>' +
        '<div>fence</div>' +
        '<div>grape</div>';

    assert.deepEqual(container.appended_data.html(), expected_html);

    // Filtering will pick out dog/egg/grape when we put "g"
    // into our search input.  (This uses the default filter, which
    // is a glorified indexOf call.)
    search_input.val = () => 'g';
    search_input.simulate_input_event();
    expected_html = '<div>dog</div><div>egg</div><div>grape</div>';
    assert.deepEqual(container.appended_data.html(), expected_html);

    // We can insert new data into the widget.
    const new_data = [
        'greta',
        'faye',
        'gary',
        'frank',
        'giraffe',
        'fox',
    ];

    widget.replace_list_data(new_data);
    expected_html =
        '<div>greta</div>' +
        '<div>gary</div>' +
        '<div>giraffe</div>';
    assert.deepEqual(container.appended_data.html(), expected_html);

    // Opts does not require a filter key.
    opts = {
        modifier: (item) => div(item),
    };
    list_render.validate_filter(opts);
    widget = list_render.create(container, ['apple', 'banana'], opts);
    widget.render();

    expected_html =
        '<div>apple</div>' +
        '<div>banana</div>';
    assert.deepEqual(container.appended_data.html(), expected_html);
});

function sort_button(opts) {
    // The complications here are due to needing to find
    // the list via complicated HTML assumptions. Also, we
    // don't have any abstraction for the button and its
    // siblings other than direct jQuery actions.

    function data(sel) {
        switch (sel) {
        case "sort": return opts.sort_type;
        case "sort-prop": return opts.prop_name;
        default: throw Error('unknown selector: ' + sel);
        }
    }

    function lookup(sel, value) {
        return (selector) => {
            assert.equal(sel, selector);
            return value;
        };
    }

    const button = {
        data: data,
        closest: lookup('.progressive-table-wrapper', {
            data: lookup('list-render', opts.list_name),
        }),
        hasClass: (sel) => {
            if (sel === 'active') {
                return opts.active;
            }
            assert.equal(sel, 'descend');
            return false;
        },
        siblings: lookup('.active', {
            removeClass: (sel) => {
                assert.equal(sel, 'active');
                button.siblings_deactivated = true;
            },
        }),
        addClass: (sel) => {
            assert.equal(sel, 'active');
            button.activated = true;
        },
        siblings_deactivated: false,
        activated: false,
    };

    return button;
}

run_test('filtering', () => {
    const lst = [
        'alexander',
        'alice',
        'benedict',
        'JESSE',
        'scott',
        'Stephanie',
        'Xavier',
    ];

    const opts = {
        filter: {
            predicate: (item, value) => {
                return item.length === value;
            },
        },
    };

    const custom_result = list_render.filter(5, lst, opts);
    assert.deepEqual(custom_result, [
        'alice',
        'JESSE',
        'scott',
    ]);

});

run_test('sorting', () => {
    const {container} = make_containers();

    let cleared;
    container.html = (html) => {
        assert.equal(html, '');
        cleared = true;
    };

    const alice = { name: 'alice', salary: 50 };
    const bob = { name: 'Bob', salary: 40 };
    const cal = { name: 'cal', salary: 30 };
    const dave = { name: 'dave', salary: 25 };

    const list = [bob, dave, alice, cal];

    const opts = {
        name: 'my-list',
        modifier: (item) => {
            return div(item.name) + div(item.salary);
        },
        filter: {
            predicate: () => true,
        },
    };

    function html_for(people) {
        return people.map(opts.modifier).join('');
    }

    const widget = list_render.create(container, list, opts);

    let button_opts;
    let button;
    let expected_html;

    button_opts = {
        sort_type: 'alphabetic',
        prop_name: 'name',
        list_name: 'my-list',
        active: false,
    };

    button = sort_button(button_opts);

    list_render.handle_sort(button, widget);

    assert(cleared);
    assert(button.siblings_deactivated);

    expected_html = html_for([alice, bob, cal, dave]);
    assert.deepEqual(container.appended_data.html(), expected_html);

    // Now try a numeric sort.
    button_opts = {
        sort_type: 'numeric',
        prop_name: 'salary',
        list_name: 'my-list',
        active: false,
    };

    button = sort_button(button_opts);

    cleared = false;
    button.siblings_deactivated = false;

    list_render.handle_sort(button, widget);

    assert(cleared);
    assert(button.siblings_deactivated);

    expected_html = html_for([dave, cal, bob, alice]);
    assert.deepEqual(container.appended_data.html(), expected_html);
});
