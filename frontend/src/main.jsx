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
import Calendar from './pages/Calendar.jsx'
import DateDetail from './pages/DateDetail.jsx'
import DateForm from './pages/DateForm.jsx'
import Dates from './pages/Dates.jsx'
import IdeaDetail from './pages/IdeaDetail.jsx'
import Ideas from './pages/Ideas.jsx'
import MapPage from './pages/Map.jsx'
import NewIdea from './pages/NewIdea.jsx'
import RecipeDetail from './pages/RecipeDetail.jsx'
import RecipeForm from './pages/RecipeForm.jsx'
import Recipes from './pages/Recipes.jsx'
import Shopping from './pages/Shopping.jsx'
import Trash from './pages/Trash.jsx'
import Join from './pages/Join.jsx'
import Space from './pages/Space.jsx'
import { registerSW } from 'virtual:pwa-register'
import './index.css'

registerSW({ immediate: true })

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
          <Route path="/space" element={<RequireAuth><Space /></RequireAuth>} />
          <Route path="/dates" element={<RequireAuth><Dates /></RequireAuth>} />
          <Route path="/map" element={<RequireAuth><MapPage /></RequireAuth>} />
          <Route path="/ideas" element={<RequireAuth><Ideas /></RequireAuth>} />
          <Route path="/calendar" element={<RequireAuth><Calendar /></RequireAuth>} />
          <Route path="/recipes" element={<RequireAuth><Recipes /></RequireAuth>} />
          <Route path="/shopping" element={<RequireAuth><Shopping /></RequireAuth>} />
          <Route path="/recipes/new" element={<RequireAuth><RecipeForm /></RequireAuth>} />
          <Route path="/recipes/:id" element={<RequireAuth><RecipeDetail /></RequireAuth>} />
          <Route path="/recipes/:id/edit" element={<RequireAuth><RecipeForm /></RequireAuth>} />
          <Route path="/ideas/new" element={<RequireAuth><NewIdea /></RequireAuth>} />
          <Route path="/ideas/:id" element={<RequireAuth><IdeaDetail /></RequireAuth>} />
          <Route path="/trash" element={<RequireAuth><Trash /></RequireAuth>} />
          <Route path="/dates/new" element={<RequireAuth><DateForm /></RequireAuth>} />
          <Route path="/dates/:id" element={<RequireAuth><DateDetail /></RequireAuth>} />
          <Route path="/dates/:id/edit" element={<RequireAuth><DateForm /></RequireAuth>} />
          <Route path="/join/:token" element={<RequireAuth><Join /></RequireAuth>} />
          <Route path="/login" element={<Login />} />
          <Route path="/invite/:token" element={<Invite />} />
          <Route path="/recover/:token" element={<Invite recovery />} />
        </Routes>
      </BrowserRouter>
      </I18nProvider>
    </QueryClientProvider>
  </StrictMode>,
)
