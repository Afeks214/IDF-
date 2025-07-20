import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { I18nextProvider } from 'react-i18next';
import { store, useAppDispatch, useAppSelector } from './store';
import { getCurrentUser, logoutUser } from './store/authSlice';
import RTLProvider from './components/providers/RTLProvider';
import PWAProvider from './components/pwa/PWAProvider';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AppLayout from './components/layout/AppLayout';
import MobileNavigation from './components/mobile/MobileNavigation';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import BuildingsPage from './pages/BuildingsPage';
import TestsPage from './pages/TestsPage';
import ReportsPage from './pages/ReportsPage';
import i18n from './locales/i18n';
import { loginUser } from './store/authSlice';

// App content component (needs to be inside Provider)
const AppContent: React.FC = () => {
  const dispatch = useAppDispatch();
  const { isAuthenticated, user, isLoading, error } = useAppSelector((state) => state.auth);

  useEffect(() => {
    // Check if user is already authenticated (token exists)
    const token = localStorage.getItem('token');
    if (token && !user) {
      dispatch(getCurrentUser());
    }
  }, [dispatch, user]);

  const handleLogin = async (credentials: any) => {
    await dispatch(loginUser(credentials));
  };

  const handleLogout = () => {
    dispatch(logoutUser());
  };

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '18px'
      }}>
        טוען...
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <LoginPage
                onLogin={handleLogin}
                loading={isLoading}
                error={error}
              />
            )
          }
        />

        {/* Protected routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout onLogout={handleLogout} user={user ? { name: user.name, role: user.role } : undefined}>
                <DashboardPage />
              </AppLayout>
              <MobileNavigation />
            </ProtectedRoute>
          }
        />

        <Route
          path="/buildings"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout onLogout={handleLogout} user={user ? { name: user.name, role: user.role } : undefined}>
                <BuildingsPage />
              </AppLayout>
              <MobileNavigation />
            </ProtectedRoute>
          }
        />

        <Route
          path="/tests"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout onLogout={handleLogout} user={user ? { name: user.name, role: user.role } : undefined}>
                <TestsPage />
              </AppLayout>
              <MobileNavigation />
            </ProtectedRoute>
          }
        />

        <Route
          path="/reports"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout onLogout={handleLogout} user={user ? { name: user.name, role: user.role } : undefined}>
                <ReportsPage />
              </AppLayout>
              <MobileNavigation />
            </ProtectedRoute>
          }
        />

        {/* Default redirect */}
        <Route
          path="/"
          element={
            <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />
          }
        />

        {/* Catch all route */}
        <Route
          path="*"
          element={
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100vh',
              fontSize: '24px'
            }}>
              <h1>404 - עמוד לא נמצא</h1>
              <p>העמוד שחיפשת לא קיים במערכת</p>
            </div>
          }
        />
      </Routes>
    </Router>
  );
};

const App: React.FC = () => {
  return (
    <Provider store={store}>
      <I18nextProvider i18n={i18n}>
        <RTLProvider>
          <PWAProvider>
            <AppContent />
          </PWAProvider>
        </RTLProvider>
      </I18nextProvider>
    </Provider>
  );
};

export default App;