import pytest

from tracker.models import Profile


@pytest.mark.parametrize('fields', [
    {},
    {'name': 'Serge', 'country': 'eu'},
    {'team': 0},
    {'name': 'Serge', 'team': 0},
])
def test_unpopular_profile_raises_404(db, client, fields):
    profile = Profile.objects.create(**fields)
    response = client.get(f'/profile/{profile.pk}/')
    assert response.status_code == 404
