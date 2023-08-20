from unittest import mock

import pytest
from django.urls import reverse

from apps.tracker.tasks import merge_servers
from tests.factories.tracker import ServerFactory


@pytest.fixture
def merge_form_url():
    return reverse("admin:tracker_server_merge_form")


@pytest.fixture
def changelist_url():
    return reverse("admin:tracker_server_changelist")


@pytest.mark.parametrize(
    "term, expected",
    [
        ("1", []),
        ("1.1.1.1", ["1.1.1.1:10480", "1.1.1.1:10580"]),
        ("1.1.1.1:10480", ["1.1.1.1:10480"]),
        ("1.1.1.1:10580", ["1.1.1.1:10580"]),
        ("1.1.1.1:999999", []),
        ("1.1.1.1:-1", []),
        ("2.2.2.2", []),
        ("2.2.2.2:10480", []),
        ("Swat4Server", ["4.4.4.4:10480"]),
        ("4.4.4.4", ["4.4.4.4:10480", "5.5.5.5:10480"]),
        ("4.4.4.4:10480", ["4.4.4.4:10480"]),
        ("4.4.4.4:999999", ["5.5.5.5:10480"]),
    ],
)
def test_server_admin_search(db, admin_client, term, expected):
    """Test that the server admin search works."""
    ServerFactory(ip="1.1.1.1", port=10480)
    ServerFactory(ip="1.1.1.1", port=10580)
    ServerFactory(ip="3.3.3.3", port=10480)
    ServerFactory(ip="4.4.4.4", hostname="Swat4Server: Best VIP server", port=10480)
    ServerFactory(ip="5.5.5.5", hostname="4.4.4.4:999999", port=10480)

    url = reverse("admin:tracker_server_changelist")
    response = admin_client.get(url, {"q": term})

    actual_addrs = [obj.address for obj in response.context["cl"].queryset]
    assert actual_addrs == expected


def test_merge_action_redirects_to_merge_form(db, admin_client, merge_form_url):
    server1, server2, server3 = ServerFactory.create_batch(3)
    resp = admin_client.post(
        reverse("admin:tracker_server_changelist"),
        {"action": "merge_servers", "_selected_action": [server1.pk, server2.pk, server3.pk]},
    )
    assert resp.status_code == 302
    assert resp.url == f"{merge_form_url}?ids={server1.pk},{server2.pk},{server3.pk}"


def test_merge_action_no_servers(db, admin_client):
    resp = admin_client.post(
        reverse("admin:tracker_server_changelist"),
        {"action": "merge_servers", "_selected_action": []},
    )
    assert resp.status_code == 200


def test_merge_action_unknown_servers(db, admin_client, changelist_url):
    resp = admin_client.post(
        reverse("admin:tracker_server_changelist"),
        {"action": "merge_servers", "_selected_action": [1, 2]},
    )
    assert resp.status_code == 302
    assert resp.url == changelist_url


def test_merge_action_few_servers(db, admin_client, changelist_url):
    server = ServerFactory()
    resp = admin_client.post(
        reverse("admin:tracker_server_changelist"),
        {"action": "merge_servers", "_selected_action": [server.pk]},
    )
    assert resp.status_code == 302
    assert resp.url == changelist_url


def test_render_merge_form_choices(db, admin_client, merge_form_url):
    server1, server2, server3 = ServerFactory.create_batch(3)
    resp = admin_client.get(f"{merge_form_url}?ids={server1.pk},{server2.pk},{server3.pk}")
    assert resp.status_code == 200
    expected_choices = [(s.pk, f"{s.hostname} ({s.address})") for s in [server3, server2, server1]]
    assert resp.context["form"].fields["main_server"].choices == expected_choices
    assert resp.context["form"].fields["merged_servers"].choices == expected_choices


def test_render_merge_form_requires_admin(db, client, merge_form_url):
    resp = client.get(f"{merge_form_url}?ids=1,2,3")
    assert resp.status_code == 302
    assert resp.url.startswith(reverse("admin:login"))


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"ids": ""},
        {"ids": " "},
        {"ids": " , "},
        {"ids": "foo"},
        {"ids": ","},
        {"ids": "foo,bar"},
        {"ids": "1,foo,3"},
        {"ids": ",2"},
        {"ids": ",2,"},
        {"ids": "2,"},
    ],
)
def test_render_merge_form_no_servers(db, admin_client, merge_form_url, changelist_url, params):
    resp = admin_client.get(merge_form_url, params)
    assert resp.status_code == 302
    assert resp.url == changelist_url


@mock.patch.object(merge_servers, "apply_async")
def test_submit_merge_form_ok(task_mock, db, admin_client, merge_form_url, changelist_url):
    server1, server2, server3 = ServerFactory.create_batch(3)
    resp = admin_client.post(
        f"{merge_form_url}?ids={server1.pk},{server2.pk},{server3.pk}",
        {"main_server": server2.pk, "merged_servers": [server1.pk, server3.pk], "confirm": "yes"},
    )
    assert resp.status_code == 302
    assert resp.url == changelist_url
    task_mock.assert_called_once_with(
        (), {"main_server_id": server2.pk, "merged_server_ids": [server1.pk, server3.pk]}
    )


@mock.patch.object(merge_servers, "apply_async")
def test_main_server_is_filtered_out(task_mock, db, admin_client, merge_form_url, changelist_url):
    server1, server2, server3 = ServerFactory.create_batch(3)
    resp = admin_client.post(
        f"{merge_form_url}?ids={server1.pk},{server2.pk},{server3.pk}",
        {
            "main_server": server2.pk,
            "merged_servers": [server1.pk, server2.pk, server3.pk],
            "confirm": "yes",
        },
    )
    assert resp.status_code == 302
    assert resp.url == changelist_url
    task_mock.assert_called_once_with(
        (), {"main_server_id": server2.pk, "merged_server_ids": [server1.pk, server3.pk]}
    )


@mock.patch.object(merge_servers, "apply_async")
def test_cant_merge_server_into_itself(task_mock, db, admin_client, merge_form_url):
    server = ServerFactory()
    resp = admin_client.post(
        f"{merge_form_url}?ids={server.pk}",
        {"main_server": server.pk, "merged_servers": [server.pk], "confirm": "yes"},
    )
    assert resp.status_code == 200
    assert not resp.context["form"].is_valid()
    assert not task_mock.called


@mock.patch.object(merge_servers, "apply_async")
def test_cant_merge_into_merged_server(task_mock, db, admin_client, merge_form_url):
    server1 = ServerFactory(merged_into=ServerFactory())
    server2 = ServerFactory()
    resp = admin_client.post(
        f"{merge_form_url}?ids={server1.pk},{server2.pk}",
        {"main_server": server1.pk, "merged_servers": [server2.pk], "confirm": "yes"},
    )
    assert resp.status_code == 200
    assert not resp.context["form"].is_valid()
    assert not task_mock.called


@mock.patch.object(merge_servers, "apply_async")
def test_cant_merge_already_merged_servers(task_mock, db, admin_client, merge_form_url):
    server1, server3 = ServerFactory.create_batch(2)
    server2 = ServerFactory(merged_into=ServerFactory())
    resp = admin_client.post(
        f"{merge_form_url}?ids={server1.pk},{server2.pk},{server3.pk}",
        {"main_server": server1.pk, "merged_servers": [server2.pk, server3.pk], "confirm": "yes"},
    )
    assert resp.status_code == 200
    assert not resp.context["form"].is_valid()
    assert not task_mock.called


@mock.patch.object(merge_servers, "apply_async")
def test_merge_form_handle_empty_choices(task_mock, db, admin_client, merge_form_url):
    server1, server2, server3 = ServerFactory.create_batch(3)
    resp = admin_client.post(
        f"{merge_form_url}?ids={server1.pk}",
        {"main_server": "", "merged_servers": [], "confirm": "yes"},
    )
    assert resp.status_code == 200
    assert not resp.context["form"].is_valid()
    assert not task_mock.called


@mock.patch.object(merge_servers, "apply_async")
def test_merge_form_handle_invalid_choices(task_mock, db, admin_client, merge_form_url):
    server1, server2, server3 = ServerFactory.create_batch(3)
    resp = admin_client.post(
        f"{merge_form_url}?ids={server1.pk}",
        {"main_server": server1.pk, "merged_servers": [server2.pk, server3.pk], "confirm": "yes"},
    )
    assert resp.status_code == 200
    assert not resp.context["form"].is_valid()
    assert not task_mock.called
