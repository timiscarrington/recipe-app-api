from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import MealPlan
from recipe.serializers import MealPlanSerializer

MEAL_PLAN_URL = reverse('recipe:mealplan-list')


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a user"""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicMealPlanApiTests(TestCase):
    """Test unauthenticated API requests for MealPlan"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving meal plans"""
        res = self.client.get(MEAL_PLAN_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMealPlanApiTests(TestCase):
    """Test authenticated API requests for MealPlan"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_meal_plans(self):
        """Test retrieving a list of meal plans"""
        MealPlan.objects.create(
            user=self.user,
            start_date=date(2023, 7, 3),
            end_date=date(2023, 7, 9),
        )
        MealPlan.objects.create(
            user=self.user,
            start_date=date(2023, 7, 10),
            end_date=date(2023, 7, 16),
        )

        res = self.client.get(MEAL_PLAN_URL)

        meal_plans = MealPlan.objects.all().order_by('-start_date')
        serializer = MealPlanSerializer(meal_plans, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_meal_plans_limited_to_user(self):
        """Test list of meal plans is limited to the authenticated user"""
        user2 = create_user(email='user2@example.com')
        MealPlan.objects.create(
            user=user2,
            start_date=date(2023, 7, 3),
            end_date=date(2023, 7, 9),
        )
        meal_plan = MealPlan.objects.create(
            user=self.user,
            start_date=date(2023, 7, 10),
            end_date=date(2023, 7, 16),
        )

        res = self.client.get(MEAL_PLAN_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], meal_plan.id)

    def test_create_meal_plan(self):
        """Test creating a meal plan"""
        payload = {
            'start_date': '2023-07-10',
            'end_date': '2023-07-16',
        }
        res = self.client.post(MEAL_PLAN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        meal_plan = MealPlan.objects.get(id=res.data['id'])
        self.assertEqual(meal_plan.user, self.user)
        self.assertEqual(str(meal_plan.start_date), payload['start_date'])
        self.assertEqual(str(meal_plan.end_date), payload['end_date'])

    def test_create_meal_plan_invalid_dates(self):
        """Test creating a meal plan with invalid dates"""
        payload = {
            'start_date': '2023-07-10',
            'end_date': '2023-07-09',
        }
        res = self.client.post(MEAL_PLAN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            res.data['non_field_errors'][0],
            "End date must be greater than or equal to start date."
        )

    def test_update_meal_plan(self):
        """Test updating a meal plan"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            start_date=date(2023, 7, 10),
            end_date=date(2023, 7, 16),
        )
        payload = {
            'start_date': '2023-07-17',
            'end_date': '2023-07-23',
        }
        url = reverse('recipe:mealplan-detail', args=[meal_plan.id])
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        meal_plan.refresh_from_db()
        self.assertEqual(str(meal_plan.start_date), payload['start_date'])
        self.assertEqual(str(meal_plan.end_date), payload['end_date'])

    def test_delete_meal_plan(self):
        """Test deleting a meal plan"""
        meal_plan = MealPlan.objects.create(
            user=self.user,
            start_date=date(2023, 7, 10),
            end_date=date(2023, 7, 16),
        )
        url = reverse('recipe:mealplan-detail', args=[meal_plan.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MealPlan.objects.filter(id=meal_plan.id).exists())
