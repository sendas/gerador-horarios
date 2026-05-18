import { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: () => import('pages/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', component: () => import('pages/DashboardPage.vue') },
      { path: 'clusters', component: () => import('pages/ClustersPage.vue') },
      { path: 'schools', component: () => import('pages/SchoolsPage.vue') },
      { path: 'academic-years', component: () => import('pages/AcademicYearsPage.vue') },
      { path: 'time-slots', component: () => import('pages/TimeSlotsPage.vue') },
      { path: 'rooms', component: () => import('pages/RoomsPage.vue') },
      { path: 'subjects', component: () => import('pages/SubjectsPage.vue') },
      { path: 'classes', component: () => import('pages/ClassesPage.vue') },
      { path: 'teachers', component: () => import('pages/TeachersPage.vue') },
      { path: 'timetables', component: () => import('pages/TimetablesPage.vue') },
      { path: 'timetables/:id', component: () => import('pages/TimetableDetailPage.vue') },
      { path: 'non-teaching', component: () => import('pages/NonTeachingPage.vue') },
      { path: 'users', component: () => import('pages/UsersPage.vue'), meta: { requiresAdmin: true } },
    ],
  },
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
]

export default routes
