"""
Unit tests for getting the list of courses for a user through iterating all courses and
by reversing group name formats.
"""
from datetime import timedelta
import unittest

from django.conf import settings
from django.test.client import Client
import mock

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from student.models import CourseEnrollment
from student.roles import GlobalStaff
from student.tests.factories import UserFactory
from student.views import get_course_enrollments
from xmodule.error_module import ErrorDescriptor
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory
from util.milestones_helpers import (
    get_pre_requisite_courses_not_completed,
    set_prerequisite_courses,
    seed_milestone_relationship_types
)


class TestCourseListing(ModuleStoreTestCase):
    """
    Unit tests for getting the list of courses for a logged in user
    """
    def setUp(self):
        """
        Add a student & teacher
        """
        super(TestCourseListing, self).setUp()

        self.student = UserFactory()
        self.teacher = UserFactory()
        GlobalStaff().add_users(self.teacher)
        self.client = Client()
        self.client.login(username=self.teacher.username, password='test')

    def _create_course_with_access_groups(self, course_location, metadata=None, default_store=None):
        """
        Create dummy course with 'CourseFactory' and enroll the student
        """
        metadata = {} if not metadata else metadata
        course = CourseFactory.create(
            org=course_location.org,
            number=course_location.course,
            run=course_location.run,
            metadata=metadata,
            default_store=default_store
        )

        CourseEnrollment.enroll(self.student, course.id)

        return course

    def tearDown(self):
        """
        Reverse the setup
        """
        self.client.logout()
        super(TestCourseListing, self).tearDown()

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_get_course_list(self):
        """
        Test getting courses
        """
        course_location = self.store.make_course_key('Org1', 'Course1', 'Run1')
        self._create_course_with_access_groups(course_location)

        # get dashboard
        courses_list = list(get_course_enrollments(self.student, None, []))
        self.assertEqual(len(courses_list), 1)
        self.assertEqual(courses_list[0].course_id, course_location)

        CourseEnrollment.unenroll(self.student, course_location)
        # get dashboard
        courses_list = list(get_course_enrollments(self.student, None, []))
        self.assertEqual(len(courses_list), 0)

    @unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
    def test_get_course_list_order(self):
        """
        Test getting courses order
        """
        course_location1 = self.store.make_course_key('Org1', 'Course1', 'Run2')
        self._create_course_with_access_groups(course_location1)
        course_location2 = self.store.make_course_key('Org1', 'Course2', 'Run1')
        self._create_course_with_access_groups(course_location2)

        # enrollment value
        enrollment1 = CourseEnrollment.get_enrollment(self.student, course_location1)
        enrollment2 = CourseEnrollment.get_enrollment(self.student, course_location2)

        # mod created of enrollment same value
        enrollment1.created = enrollment2.created
        enrollment1.save()

        # non order
        enrollments_list = list(get_course_enrollments(self.student, None, []))
        self.assertEqual([e.course_id for e in enrollments_list], [course_location1, course_location2])

        # order created
        enrollments_list = list(get_course_enrollments(self.student, None, [], ('-created',)))
        self.assertEqual([e.course_id for e in enrollments_list], [course_location1, course_location2])

        # order -created,-id
        enrollments_list = list(get_course_enrollments(self.student, None, [], ('-created', '-id')))
        self.assertEqual([e.course_id for e in enrollments_list], [course_location2, course_location1])

        # mod created of enrollment different value
        enrollment2.created = enrollment1.created + timedelta(seconds=1)
        enrollment2.save()

        # non order
        enrollments_list = list(get_course_enrollments(self.student, None, []))
        self.assertEqual([e.course_id for e in enrollments_list], [course_location1, course_location2])

        # order created
        enrollments_list = list(get_course_enrollments(self.student, None, [], ('-created',)))
        self.assertEqual([e.course_id for e in enrollments_list], [course_location2, course_location1])

        # order -created,-id
        enrollments_list = list(get_course_enrollments(self.student, None, [], ('-created', '-id')))
        self.assertEqual([e.course_id for e in enrollments_list], [course_location2, course_location1])

    def test_errored_course_regular_access(self):
        """
        Test the course list for regular staff when get_course returns an ErrorDescriptor
        """
        # pylint: disable=protected-access
        mongo_store = modulestore()._get_modulestore_by_type(ModuleStoreEnum.Type.mongo)
        course_key = mongo_store.make_course_key('Org1', 'Course1', 'Run1')
        self._create_course_with_access_groups(course_key, default_store=ModuleStoreEnum.Type.mongo)

        with mock.patch('xmodule.modulestore.mongo.base.MongoKeyValueStore', mock.Mock(side_effect=Exception)):
            self.assertIsInstance(modulestore().get_course(course_key), ErrorDescriptor)

            # Invalidate (e.g., delete) the corresponding CourseOverview, forcing get_course to be called.
            CourseOverview.objects.filter(id=course_key).delete()

            courses_list = list(get_course_enrollments(self.student, None, []))
            self.assertEqual(courses_list, [])

    def test_course_listing_errored_deleted_courses(self):
        """
        Create good courses, courses that won't load, and deleted courses which still have
        roles. Test course listing.
        """
        mongo_store = modulestore()._get_modulestore_by_type(ModuleStoreEnum.Type.mongo)

        good_location = mongo_store.make_course_key('testOrg', 'testCourse', 'RunBabyRun')
        self._create_course_with_access_groups(good_location, default_store=ModuleStoreEnum.Type.mongo)

        course_location = mongo_store.make_course_key('testOrg', 'doomedCourse', 'RunBabyRun')
        self._create_course_with_access_groups(course_location, default_store=ModuleStoreEnum.Type.mongo)
        mongo_store.delete_course(course_location, ModuleStoreEnum.UserID.test)

        courses_list = list(get_course_enrollments(self.student, None, []))
        self.assertEqual(len(courses_list), 1, courses_list)
        self.assertEqual(courses_list[0].course_id, good_location)

    @mock.patch.dict("django.conf.settings.FEATURES", {'ENABLE_PREREQUISITE_COURSES': True, 'MILESTONES_APP': True})
    def test_course_listing_has_pre_requisite_courses(self):
        """
        Creates four courses. Enroll test user in all courses
        Sets two of them as pre-requisites of another course.
        Checks course where pre-requisite course is set has appropriate info.
        """
        seed_milestone_relationship_types()
        course_location2 = self.store.make_course_key('Org1', 'Course2', 'Run2')
        self._create_course_with_access_groups(course_location2)
        pre_requisite_course_location = self.store.make_course_key('Org1', 'Course3', 'Run3')
        self._create_course_with_access_groups(pre_requisite_course_location)
        pre_requisite_course_location2 = self.store.make_course_key('Org1', 'Course4', 'Run4')
        self._create_course_with_access_groups(pre_requisite_course_location2)
        # create a course with pre_requisite_courses
        pre_requisite_courses = [
            unicode(pre_requisite_course_location),
            unicode(pre_requisite_course_location2),
        ]
        course_location = self.store.make_course_key('Org1', 'Course1', 'Run1')
        self._create_course_with_access_groups(course_location, {
            'pre_requisite_courses': pre_requisite_courses
        })

        set_prerequisite_courses(course_location, pre_requisite_courses)
        # get dashboard
        course_enrollments = list(get_course_enrollments(self.student, None, []))
        courses_having_prerequisites = frozenset(
            enrollment.course_id for enrollment in course_enrollments
            if enrollment.course_overview.pre_requisite_courses
        )
        courses_requirements_not_met = get_pre_requisite_courses_not_completed(
            self.student,
            courses_having_prerequisites
        )
        self.assertEqual(len(courses_requirements_not_met[course_location]['courses']), len(pre_requisite_courses))
