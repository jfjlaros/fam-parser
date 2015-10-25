"use strict";

var webpack = require("webpack");

module.exports = {
  entry: "./javascript/src/index.js",
  module: {
    loaders: [{
        test: /\.json$/,
        loader: "json"
      }, {
        test: /\.yml$/,
        loader: "json!yaml"
      }
    ]
  },
  output: {
    filename: "index.js",
    libraryTarget: "commonjs2",
    path: __dirname + "/javascript/dist"
  },
  plugins: [
    new webpack.optimize.AggressiveMergingPlugin(),
    new webpack.optimize.DedupePlugin(),
    new webpack.optimize.OccurenceOrderPlugin(),
    new webpack.optimize.UglifyJsPlugin()
  ],
  target: "node"
};
