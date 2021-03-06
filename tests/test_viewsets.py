import pytest
from django.conf.urls import include, url
from django.db import models
from django.test import TestCase, override_settings

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import SimpleRouter
from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import GenericViewSet

factory = APIRequestFactory()


class BasicViewSet(GenericViewSet):
    def list(self, request, *args, **kwargs):
        return Response({'ACTION': 'LIST'})


class InstanceViewSet(GenericViewSet):

    def dispatch(self, request, *args, **kwargs):
        return self.dummy(request, *args, **kwargs)

    def dummy(self, request, *args, **kwargs):
        return Response({'view': self})


class Action(models.Model):
    pass


class ActionViewSet(GenericViewSet):
    queryset = Action.objects.all()

    def list(self, request, *args, **kwargs):
        raise NotImplementedError

    def retrieve(self, request, *args, **kwargs):
        raise NotImplementedError

    @action(detail=False)
    def list_action(self, request, *args, **kwargs):
        raise NotImplementedError

    @action(detail=False, url_name='list-custom')
    def custom_list_action(self, request, *args, **kwargs):
        raise NotImplementedError

    @action(detail=True)
    def detail_action(self, request, *args, **kwargs):
        raise NotImplementedError

    @action(detail=True, url_name='detail-custom')
    def custom_detail_action(self, request, *args, **kwargs):
        raise NotImplementedError


router = SimpleRouter()
router.register(r'actions', ActionViewSet)
router.register(r'actions-alt', ActionViewSet, base_name='actions-alt')


urlpatterns = [
    url(r'^api/', include(router.urls)),
]


class InitializeViewSetsTestCase(TestCase):
    def test_initialize_view_set_with_actions(self):
        request = factory.get('/', '', content_type='application/json')
        my_view = BasicViewSet.as_view(actions={
            'get': 'list',
        })

        response = my_view(request)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'ACTION': 'LIST'}

    def testhead_request_against_viewset(self):
        request = factory.head('/', '', content_type='application/json')
        my_view = BasicViewSet.as_view(actions={
            'get': 'list',
        })

        response = my_view(request)
        assert response.status_code == status.HTTP_200_OK

    def test_initialize_view_set_with_empty_actions(self):
        with pytest.raises(TypeError) as excinfo:
            BasicViewSet.as_view()

        assert str(excinfo.value) == (
            "The `actions` argument must be provided "
            "when calling `.as_view()` on a ViewSet. "
            "For example `.as_view({'get': 'list'})`")

    def test_args_kwargs_request_action_map_on_self(self):
        """
        Test a view only has args, kwargs, request, action_map
        once `as_view` has been called.
        """
        bare_view = InstanceViewSet()
        view = InstanceViewSet.as_view(actions={
            'get': 'dummy',
        })(factory.get('/')).data['view']

        for attribute in ('args', 'kwargs', 'request', 'action_map'):
            self.assertNotIn(attribute, dir(bare_view))
            self.assertIn(attribute, dir(view))


class GetExtraActionTests(TestCase):

    def test_extra_actions(self):
        view = ActionViewSet()
        actual = [action.__name__ for action in view.get_extra_actions()]
        expected = ['custom_detail_action', 'custom_list_action', 'detail_action', 'list_action']

        self.assertEqual(actual, expected)


@override_settings(ROOT_URLCONF='tests.test_viewsets')
class ReverseActionTests(TestCase):
    def test_default_basename(self):
        view = ActionViewSet()
        view.basename = router.get_default_base_name(ActionViewSet)
        view.request = None

        assert view.reverse_action('list') == '/api/actions/'
        assert view.reverse_action('list-action') == '/api/actions/list_action/'
        assert view.reverse_action('list-custom') == '/api/actions/custom_list_action/'

        assert view.reverse_action('detail', args=['1']) == '/api/actions/1/'
        assert view.reverse_action('detail-action', args=['1']) == '/api/actions/1/detail_action/'
        assert view.reverse_action('detail-custom', args=['1']) == '/api/actions/1/custom_detail_action/'

    def test_custom_basename(self):
        view = ActionViewSet()
        view.basename = 'actions-alt'
        view.request = None

        assert view.reverse_action('list') == '/api/actions-alt/'
        assert view.reverse_action('list-action') == '/api/actions-alt/list_action/'
        assert view.reverse_action('list-custom') == '/api/actions-alt/custom_list_action/'

        assert view.reverse_action('detail', args=['1']) == '/api/actions-alt/1/'
        assert view.reverse_action('detail-action', args=['1']) == '/api/actions-alt/1/detail_action/'
        assert view.reverse_action('detail-custom', args=['1']) == '/api/actions-alt/1/custom_detail_action/'

    def test_request_passing(self):
        view = ActionViewSet()
        view.basename = router.get_default_base_name(ActionViewSet)
        view.request = factory.get('/')

        # Passing the view's request object should result in an absolute URL.
        assert view.reverse_action('list') == 'http://testserver/api/actions/'

        # Users should be able to explicitly not pass the view's request.
        assert view.reverse_action('list', request=None) == '/api/actions/'
