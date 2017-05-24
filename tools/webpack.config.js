var path = require('path');

module.exports =  {
    context: path.resolve(__dirname, "../"),
    entry: {
        translations: ['./static/js/translations.js'],
    },
    output: {
        path: path.resolve(__dirname, '../static/webpack-bundles'),
        filename: '[name].js',
    },
    plugins: [],
};
