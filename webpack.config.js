const webpack = require('webpack');
const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

const isProd = process.env.NODE_ENV === 'production';

const srcPath = path.join(__dirname, 'web', 'src'),
      distPath = path.join(__dirname, 'web', 'dist', 'app');

const entry = {
  'vendor': [
    'jquery',
  ],
  'app': [
    './less/base.less',
    './css/fonts.css',
    './css/reset.css',
  ],
};

let plugins = [
  new MiniCssExtractPlugin({
    filename: '[name].css',
  }),
  new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
      'window.jQuery': 'jquery',
      'window.$': 'jquery',
    }),
];

module.exports = {
  mode: isProd ? 'production' : 'development',
  entry: entry,
  context: srcPath,
  plugins: plugins,
  resolve: {
    modules: ['node_modules', path.resolve(srcPath)],
    extensions: ['.js']
  },
  optimization: {
   minimize: isProd,
  },
  output: {
    path: path.join(distPath),
    filename: '[name].js',
  },
  devtool: 'inline-source-map',
  module: {
    rules: [
      {
        test: require.resolve("jquery"),
        loader: "expose-loader",
        options: {
          exposes: ["$", "jQuery"],
        },
      },
      {
        test: /\.css$/,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader'
        ]
      },
      {
        test: /\.less$/,
        include: srcPath,
        use: [
          MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader',
          },
          {
            loader: 'resolve-url-loader',
          },
          {
            loader: 'less-loader',
            options: {
              sourceMap: true,
              lessOptions: {
                math: 'always',
              },
            },
          }
        ]
      },
    ]
  }
};
