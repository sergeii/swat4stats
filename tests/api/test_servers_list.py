from apps.tracker.factories import (ServerFactory, ServerStatusFactory)


def test_get_server_list(db, api_client):
    ServerFactory(listed=False)
    ServerFactory(listed=True)
    ServerFactory(enabled=False, listed=True, status=ServerStatusFactory())
    ServerFactory(listed=True, status=None)
    vip_server = ServerFactory(listed=True,
                               status=ServerStatusFactory(gametype='VIP Escort',
                                                          numplayers=16,
                                                          maxplayers=16))
    pinned_server = ServerFactory(listed=True,
                                  pinned=True,
                                  status=ServerStatusFactory(gametype='VIP Escort',
                                                             numplayers=16,
                                                             maxplayers=16))
    vip_server10 = ServerFactory(listed=True,
                                 status=ServerStatusFactory(gametype='VIP Escort',
                                                            numplayers=15,
                                                            maxplayers=18,
                                                            gamever='1.0'))
    bs_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='Barricaded Suspects'))
    coop_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='CO-OP'))
    sg_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='Smash And Grab',
                                                                      gamevariant='SWAT 4X',
                                                                      gamever='1.0'))
    tss_coop_server = ServerFactory(listed=True, status=ServerStatusFactory(gametype='CO-OP',
                                                                            gamevariant='SWAT 4X',
                                                                            gamever='1.0'))
    passworded_server = ServerFactory(listed=True,
                                      status=ServerStatusFactory(password=True))

    response = api_client.get('/api/servers/')
    listed_servers = [obj['id'] for obj in response.data]

    assert response.status_code == 200
    assert isinstance(response.data, list)
    assert len(listed_servers) == 8
    assert listed_servers == [vip_server.pk, pinned_server.pk, vip_server10.pk,
                              bs_server.pk, coop_server.pk, sg_server.pk,
                              tss_coop_server.pk, passworded_server.pk]
    vip_server_obj = response.data[0]
    assert vip_server_obj['pinned'] is False
    vip_server_status = vip_server_obj['status']
    assert vip_server_status['hostname'] == 'Swat4 Server'
    assert vip_server_status['gametype'] == 'VIP Escort'
    assert 'players' not in vip_server_status
    assert 'time_round' not in vip_server_status

    pinned_server_obj = response.data[1]
    assert pinned_server_obj['pinned'] is True

    responses = [
        ({'empty': 'true'}, [bs_server.pk, coop_server.pk, sg_server.pk,
                             tss_coop_server.pk, passworded_server.pk]),
        ({'passworded': 'true'}, [passworded_server.pk]),
        ({'passworded': 'false'}, [vip_server.pk, pinned_server.pk, vip_server10.pk,
                                   bs_server.pk, coop_server.pk, sg_server.pk, tss_coop_server.pk]),
        ({'empty': 'false'}, [vip_server.pk, pinned_server.pk, vip_server10.pk]),
        ({'empty': 'false', 'full': 'false'}, [vip_server10.pk]),
        ({'empty': 'true', 'full': 'true'}, []),
        ({'empty': 'false', 'full': 'true'}, [vip_server.pk, pinned_server.pk]),
        ({'full': 'true', 'gametype': 'VIP Escort'}, [vip_server.pk, pinned_server.pk]),
        ({'full': 'true', 'gametype': 'CO-OP'}, []),
        ({'gametype': 'CO-OP'}, [coop_server.pk, tss_coop_server.pk]),
        ({'gamename': 'SWAT 4X'}, [sg_server.pk, tss_coop_server.pk]),
        ({'gamename': 'SWAT 4X', 'gametype': 'VIP Escort'}, []),
        ({'gamename': 'SWAT 4X', 'full': 'true'}, []),
        ({'gamename': 'SWAT 4X', 'full': 'False'}, [sg_server.pk, tss_coop_server.pk]),
        ({'gamever': '1.1'}, [vip_server.pk, pinned_server.pk,
                              bs_server.pk, coop_server.pk, passworded_server.pk]),
        ({'gamever': '1.0'}, [vip_server10.pk, sg_server.pk, tss_coop_server.pk]),
        ({'gamever': '1.1', 'gamename': 'SWAT 4X'}, []),
        ({'gamever': '1.1', 'gamename': 'SWAT 4'}, [vip_server.pk, pinned_server.pk,
                                                    bs_server.pk, coop_server.pk, passworded_server.pk]),
        ({'gamever': '1.0', 'gamename': 'SWAT 4'}, [vip_server10.pk]),
        ({'gamever': '1.0', 'gamename': 'SWAT 4', 'gametype': 'Smash And Grab'}, []),
        ({'gamever': '1.0', 'gamename': 'SWAT 4X'}, [sg_server.pk, tss_coop_server.pk]),
        ({'gamename': 'Invalid'}, []),
        ({'gametype': 'Unknown'}, []),
    ]

    for filters, expected_data in responses:
        response = api_client.get('/api/servers/', data=filters)
        assert [obj['id'] for obj in response.data] == expected_data, filters
