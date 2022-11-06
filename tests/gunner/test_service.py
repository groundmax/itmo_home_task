import typing as tp
from http import HTTPStatus

import pytest
from aiohttp import ClientSession
from pydantic import ValidationError
from pytest_httpserver import HTTPServer, HeaderValueMatcher

from requestor.gunner import (
    AuthorizationError,
    DuplicatedRecommendationsError,
    GunnerService,
    HugeResponseSizeError,
    RecommendationsLimitSizeError,
    RequestLimitByUserError,
)
from requestor.settings import ServiceConfig
from tests.utils import (
    ResponseTypes,
    gen_json_reco_response,
    gen_model_user_reco_response,
    prepare_http_responses,
)

pytestmark = pytest.mark.asyncio


class TestGunnerAuth:
    @pytest.mark.parametrize("model_name", ("model_1", "model_2"))
    async def test_get_recos_success(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
        auth_headers: tp.Dict[str, str],
        header_value_matcher: HeaderValueMatcher,
        api_token: str,
        model_name: str,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size

        expected = []
        for users_batch in users_batches:
            for user_id in users_batch:
                response = gen_json_reco_response(user_id, reco_size)
                httpserver.expect_request(
                    f"/{model_name}/{user_id}",
                    headers=auth_headers,
                    header_value_matcher=header_value_matcher,
                ).respond_with_json(
                    response,
                )
                expected.append(gen_model_user_reco_response(user_id, reco_size))

        # httpserver.url_for("/") gives http://localhost:{port}//
        # but it works anyway
        actual = await gunner_service.get_recos(
            httpserver.url_for("/"),
            model_name,
            api_token=api_token,
        )

        assert actual == expected

    async def test_get_recos_auth_error(
        self,
        httpserver: HTTPServer,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
        auth_headers: tp.Dict[str, str],
        header_value_matcher: HeaderValueMatcher,
        api_token: str,
    ) -> None:
        httpserver.expect_request(
            "/health",
            headers=auth_headers,
            header_value_matcher=header_value_matcher,
        ).respond_with_data("DATA", status=HTTPStatus.UNAUTHORIZED)

        for users_batch in users_batches:
            for user_id in users_batch:
                httpserver.expect_request(
                    f"/model_name/{user_id}",
                    headers=auth_headers,
                    header_value_matcher=header_value_matcher,
                ).respond_with_data(
                    "DATA",
                    status=HTTPStatus.UNAUTHORIZED,
                )

        with pytest.raises(AuthorizationError):
            await gunner_service.get_recos(
                httpserver.url_for("/"),
                "model_name",
                api_token=api_token,
            )

    @pytest.mark.parametrize(
        "headers,response_status",
        (
            ({"Authorization": "Bearer ApiToken"}, HTTPStatus.OK),
            ({"Authorization": "Bearer IncorrectToken"}, HTTPStatus.UNAUTHORIZED),
            ({"Authorization": "Bearer IncorrectToken"}, HTTPStatus.FORBIDDEN),
        ),
    )
    async def test_ping(
        self,
        httpserver: HTTPServer,
        gunner_service: GunnerService,
        header_value_matcher: HeaderValueMatcher,
        headers: tp.Dict[str, str],
        response_status: HTTPStatus,
    ) -> None:
        httpserver.expect_request(
            "/health",
            headers=headers,
            header_value_matcher=header_value_matcher,
        ).respond_with_data("DATA", status=response_status)

        async with ClientSession(headers=headers) as session:
            status = await gunner_service.ping(session, httpserver.url_for("/"))

        assert status == response_status

    async def test_ping_no_auth_in_health_but_auth_in_session(
        self,
        httpserver: HTTPServer,
        gunner_service: GunnerService,
        auth_headers: tp.Dict[str, str],
    ) -> None:
        httpserver.expect_request(
            "/health",
        ).respond_with_data("DATA", status=HTTPStatus.OK)

        async with ClientSession(headers=auth_headers) as session:
            status = await gunner_service.ping(session, httpserver.url_for("/"))

        assert status == HTTPStatus.OK


class TestGunnerNoAuth:
    @pytest.mark.parametrize("model_name", ("model_1", "model_2"))
    async def test_get_recos_success(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
        model_name: str,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size
        httpserver.expect_request("/health").respond_with_data("DATA")

        expected = []
        for users_batch in users_batches:
            for user_id in users_batch:
                response = gen_json_reco_response(user_id, reco_size)
                httpserver.expect_request(f"/{model_name}/{user_id}").respond_with_json(response)
                expected.append(gen_model_user_reco_response(user_id, reco_size))

        # httpserver.url_for("/") gives http://localhost:{port}//
        # but it works anyway
        actual = await gunner_service.get_recos(
            httpserver.url_for("/"),
            model_name,
        )

        assert actual == expected

    async def test_ping_success(
        self,
        httpserver: HTTPServer,
        gunner_service: GunnerService,
    ) -> None:
        httpserver.expect_request("/health").respond_with_data("DATA")

        async with ClientSession() as session:
            status = await gunner_service.ping(session, httpserver.url_for("/"))

        assert status == HTTPStatus.OK

    @pytest.mark.parametrize(
        "http_status",
        (
            HTTPStatus.INTERNAL_SERVER_ERROR,
            HTTPStatus.NOT_FOUND,
            HTTPStatus.BAD_GATEWAY,
        ),
    )
    async def test_get_recos_http_status_not_ok(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
        http_status: int,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size
        httpserver.expect_request("/health").respond_with_data("DATA")

        for users_batch in users_batches:
            for user_id in users_batch:
                response = gen_json_reco_response(user_id, reco_size)
                httpserver.expect_request(f"/model_name/{user_id}").respond_with_json(
                    response,
                    status=http_status,
                )

        with pytest.raises(RequestLimitByUserError, match=rf"HTTPError: {http_status}"):
            await gunner_service.get_recos(
                httpserver.url_for("/"),
                "model_name",
            )

    # wanted to use parametrize, but it doesn't work with enum
    # I didn't find a way make it work without stupid duct tape
    # that's why decided to leave more code
    async def test_get_recos_incorrect_model_response(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size

        prepare_http_responses(
            httpserver, users_batches, reco_size, ResponseTypes.incorrect_model_response
        )

        with pytest.raises(ValidationError):
            await gunner_service.get_recos(
                httpserver.url_for("/"),
                "model_name",
            )

    async def test_get_recos_response_contains_none_in_items(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size

        prepare_http_responses(httpserver, users_batches, reco_size, ResponseTypes.contains_null)

        with pytest.raises(ValidationError):
            await gunner_service.get_recos(
                httpserver.url_for("/"),
                "model_name",
            )

    async def test_get_recos_response_contains_duplicated_items(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size

        prepare_http_responses(
            httpserver, users_batches, reco_size, ResponseTypes.contains_duplicates
        )

        with pytest.raises(DuplicatedRecommendationsError):
            await gunner_service.get_recos(
                httpserver.url_for("/"),
                "model_name",
            )

    async def test_get_recos_incorrect_reco_size(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size

        prepare_http_responses(
            httpserver, users_batches, reco_size, ResponseTypes.incorrect_reco_size
        )

        with pytest.raises(RecommendationsLimitSizeError):
            await gunner_service.get_recos(
                httpserver.url_for("/"),
                "model_name",
            )

    async def test_get_recos_huge_response_size(
        self,
        httpserver: HTTPServer,
        service_config: ServiceConfig,
        users_batches: tp.List[tp.List[int]],
        gunner_service: GunnerService,
    ) -> None:
        reco_size = service_config.assessor_config.reco_size

        prepare_http_responses(httpserver, users_batches, reco_size, ResponseTypes.huge_bytes_size)

        with pytest.raises(HugeResponseSizeError):
            await gunner_service.get_recos(
                httpserver.url_for("/"),
                "model_name",
            )
