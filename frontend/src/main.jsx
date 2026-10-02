import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RequireAuth from './components/RequireAuth.jsx'
import { I18nProvider } from './i18n/index.jsx'
import Home from './pages/Home.jsx'
import Invite from './pages/Invite.jsx'
import Login from './pages/Login.jsx'
import Settings from './pages/Settings.jsx'
import Admin from './pages/Admin.jsx'
import './index.css'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RequireAuth><Home /></RequireAuth>} />
          <Route path="/settings" element={<RequireAuth><Settings /></RequireAuth>} />
          <Route path="/admin" element={<RequireAuth><Admin /></RequireAuth>} />
          <Route path="/login" element={<Login />} />
          <Route path="/invite/:token" element={<Invite />} />
          <Route path="/recover/:token" element={<Invite recovery />} />
        </Routes>
      </BrowserRouter>
      </I18nProvider>
    </QueryClientProvider>
  </StrictMode>,
)
