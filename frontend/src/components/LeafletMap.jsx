import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const SLOVENIA = [46.15, 14.99]
const heart = L.divIcon({ html: '❤️', className: 'text-2xl leading-none', iconSize: [24, 24], iconAnchor: [12, 20] })

// Thin Leaflet wrapper with OpenStreetMap tiles. markers: [{id, lat, lon, popup?}]
export default function LeafletMap({ markers = [], onPick, className = 'h-72', fit = true }) {
  const el = useRef(null)
  const map = useRef(null)
  const layer = useRef(null)
  const pick = useRef(onPick)
  pick.current = onPick

  useEffect(() => {
    map.current = L.map(el.current).setView(SLOVENIA, 7)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap',
    }).addTo(map.current)
    layer.current = L.layerGroup().addTo(map.current)
    map.current.on('click', (e) => pick.current?.(e.latlng.lat, e.latlng.lng))
    return () => map.current.remove()
  }, [])

  useEffect(() => {
    layer.current.clearLayers()
    const points = markers.map((m) => {
      const marker = L.marker([m.lat, m.lon], { icon: heart }).addTo(layer.current)
      if (m.popup) marker.bindPopup(m.popup)
      return [m.lat, m.lon]
    })
    if (fit && points.length === 1) map.current.setView(points[0], 13)
    else if (fit && points.length > 1) map.current.fitBounds(points, { padding: [30, 30] })
  }, [markers, fit])

  return <div ref={el} className={`${className} w-full rounded-2xl`} />
}
