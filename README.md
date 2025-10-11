# swat4stats.com backend
[![License: MIT][license-img]][license]
[![Powered by Python][python-img]][python]
[![Made with Django][django-img]][django]
[![Ruff][ruff-img]][ruff]
[![codecov][codecov-img]][codecov]
[![ci][ci-img]][ci]

swat4stats.com is a full-featured player and server statistics service for [SWAT 4][swat4].

This repository contains the source code for the backend of [swat4stats.com](https://swat4stats.com).

You might also be interested in other projects that make up swat4stats.com:

- [swat4stats.com][swat4stats-web] - the web frontend of swat4stats.com
- [swat4master][swat4master] - the master server service that provides the in-game server list infrastructure

## Public API
swat4stats.com offers a public API for SWAT 4 game servers.
If you run a server, the API allows you to enable stat tracking for your server,
display leaderboards in-game, and even provide an admin interface for player identification.

For details, please refer to the [Server API documentation](docs/server_api.md).

## Getting started

Firstly, you'll want to set up your own configuration using a .env file:

```shell
cp .env.example .env
```

The development server is set to work with the default variables out of the box.
However, if needed, you can modify these variables later for a more personalized setup.

Run the development server stack:
```shell
docker compose up
```
This will start the development server on port 8000.

PostgreSQL and Redis instances that come with the development stack
use the ports 5432 and 6379, respectively.
These are exposed on your machine as well.

Apply the migrations:
```shell
docker compose exec runserver python manage.py migrate
```

If you wish, you can also set up a user with this command:
```shell
docker compose exec runserver python manage.py createuser your-cool-username --email=yours@domain.tld --password=strong --superuser
```

Once done, you'll be able to access the development server at `localhost:8000`.
For example:
* The django admin panel is at [/admin/](http://localhost:8000/admin/)
* The swagger documentation is at [/api/](http://localhost:8000/api/)

⚠️ Important: The database container running with the dev server is **not persistent**.
When you stop the development stack, the data goes away.

💡 If you want your changes to stick around, consider running a separate PostgreSQL instance.
You can then adjust the `SETTINGS_DB_*` variables accordingly.

## Testing

⚠️ For the test suite to work, it needs both PostgreSQL and Redis. Ensure the development stack is up and running.

Running the test suite is as straightforward as:
```shell
pytest
```

## Contributing
Spotted a bug, a typo, or something else that you are willing to improve? Contributions are welcome!
Please check out the [contribution guidelines](CONTRIBUTING.md).

## License

Released under the [MIT License](LICENSE.txt).

[license-img]: https://img.shields.io/badge/License-MIT-yellow.svg
[license]: https://opensource.org/licenses/MIT

[python-img]: https://img.shields.io/badge/python-3.14-blue.svg
[python]: https://www.python.org/downloads/release/python-3140/

[django-img]: https://img.shields.io/badge/django-5.1-blue.svg
[django]: https://docs.djangoproject.com/en/5.1/

[ruff-img]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff]: https://github.com/astral-sh/ruff

[codecov-img]: https://codecov.io/gh/sergeii/swat4stats/branch/main/graph/badge.svg?token=Op7MD4RMYC
[codecov]: https://codecov.io/gh/sergeii/swat4stats

[ci-img]: https://github.com/sergeii/swat4stats/actions/workflows/ci.yml/badge.svg?branch=main
[ci]: https://github.com/sergeii/swat4stats/actions/workflows/ci.yml

[swat4]: https://en.wikipedia.org/wiki/SWAT_4

[swat4stats-web]: https://github.com/sergeii/swat4stats.com
[swat4master]: https://github.com/sergeii/swat4master
