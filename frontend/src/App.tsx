import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import LoadingScreen from './components/LoadingScreen'

const Login = lazy(() => import('./pages/Login'))
const Signup = lazy(() => import('./pages/Signup'))
const Onboarding = lazy(() => import('./pages/Onboarding'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Chat = lazy(() => import('./pages/Chat'))
const History = lazy(() => import('./pages/History'))
const Subjects = lazy(() => import('./pages/Subjects'))
const SubjectDetail = lazy(() => import('./pages/SubjectDetail'))
const ChapterDetail = lazy(() => import('./pages/ChapterDetail'))
const Reader = lazy(() => import('./pages/Reader'))
const Quiz = lazy(() => import('./pages/Quiz'))
const Progress = lazy(() => import('./pages/Progress'))
const Uploads = lazy(() => import('./pages/Uploads'))
const Premium = lazy(() => import('./pages/Premium'))
const Profile = lazy(() => import('./pages/Profile'))
const Settings = lazy(() => import('./pages/Settings'))
const AdminLayout = lazy(() => import('./pages/admin/AdminLayout'))
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'))
const AdminStudents = lazy(() => import('./pages/admin/AdminStudents'))
const AdminSubjects = lazy(() => import('./pages/admin/AdminSubjects'))
const AdminChapters = lazy(() => import('./pages/admin/AdminChapters'))
const AdminKnowledge = lazy(() => import('./pages/admin/AdminKnowledge'))
const AdminSubscriptions = lazy(() => import('./pages/admin/AdminSubscriptions'))
const AdminAnalytics = lazy(() => import('./pages/admin/AdminAnalytics'))

function Protected({ children, admin = false }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingScreen />
  if (!user) return <Navigate to="/login" replace />
  if (admin && user.role !== 'admin') return <Navigate to="/dashboard" replace />
  if (!user.onboarded && !location.pathname.startsWith('/onboarding')) {
    return <Navigate to="/onboarding" replace />
  }
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<LoadingScreen />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/onboarding" element={<Onboarding />} />

          <Route element={<Protected><Layout /></Protected>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/chat/:conversationId" element={<Chat />} />
            <Route path="/history" element={<History />} />
            <Route path="/subjects" element={<Subjects />} />
            <Route path="/subjects/:subjectId" element={<SubjectDetail />} />
            <Route path="/chapters/:chapterId" element={<ChapterDetail />} />
            <Route path="/read/:chapterId" element={<Reader />} />
            <Route path="/quiz" element={<Quiz />} />
            <Route path="/progress" element={<Progress />} />
            <Route path="/uploads" element={<Uploads />} />
            <Route path="/premium" element={<Premium />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          <Route path="/admin" element={<Protected admin><AdminLayout /></Protected>}>
            <Route index element={<AdminDashboard />} />
            <Route path="students" element={<AdminStudents />} />
            <Route path="subjects" element={<AdminSubjects />} />
            <Route path="chapters" element={<AdminChapters />} />
            <Route path="knowledge" element={<AdminKnowledge />} />
            <Route path="subscriptions" element={<AdminSubscriptions />} />
            <Route path="analytics" element={<AdminAnalytics />} />
          </Route>

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  )
}
