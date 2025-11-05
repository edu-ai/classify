'use client'

import { useEffect, useState, useRef } from 'react'
import { useSession } from 'next-auth/react'
import Header from '@/components/Header/Header'
import Sidebar from '@/components/Sidebar/Sidebar'
import PhotoGallery from '@/components/PhotoGallery'
import PhotoStatistics from '@/components/PhotoStatistics'
import PhotoClearGallery from '@/components/PhotoClearGallery'
import PhotoBlurredGallery from '@/components/PhotoBlurredGallery'
import DebugInfo from '@/components/DebugInfo'
import { Photo } from '@/types'

declare global {
  interface Window {
    gapi: any
    google: any
  }
}

export default function Home() {
  const { data: session, } = useSession()
  const [apiStatus, setApiStatus] = useState<string>('checking...')
  const [pickerSessionId, setPickerSessionId] = useState<string>('')
  const [photos, setPhotos] = useState<Photo[]>([])
  const [photosLoading, setPhotosLoading] = useState(false)
  const [photosError, setPhotosError] = useState<string | null>(null);
  const [albumLoading, setAlbumLoading] = useState(false)
  const expiredAlertShown = useRef(false)
  const [servicesStatus, setServicesStatus] = useState({
    apiGateway: 'checking...',
    authService: 'checking...',
    photosService: 'checking...',
    blurDetectionService: 'checking...',
  })
  const [activeTab, setActiveTab] = useState('gallery')

  useEffect(() => {
    const checkServices = async () => {
      try {
        const gatewayResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/health`)
        if (gatewayResponse.ok) {
          setApiStatus('connected')
          setServicesStatus(prev => ({ ...prev, apiGateway: 'connected' }))
        }
      } catch {
        setApiStatus('disconnected')
        setServicesStatus(prev => ({ ...prev, apiGateway: 'disconnected' }))
      }

      try {
        const authResponse = await fetch(`${process.env.NEXT_PUBLIC_AUTH_URL}/api/health`)
        setServicesStatus(prev => ({
          ...prev,
          authService: authResponse.ok ? 'connected' : 'disconnected'
        }))
      } catch {
        setServicesStatus(prev => ({ ...prev, authService: 'disconnected' }))
      }

      try {
        const photosResponse = await fetch(`${process.env.NEXT_PUBLIC_PHOTOS_URL}/api/health`)
        setServicesStatus(prev => ({
          ...prev,
          photosService: photosResponse.ok ? 'connected' : 'disconnected'
        }))
      } catch {
        setServicesStatus(prev => ({ ...prev, photosService: 'disconnected' }))
      }

      try {
        const blurDetectionResponse = await fetch(`${process.env.NEXT_PUBLIC_BLUR_DETECTION_URL}/api/health`)
        setServicesStatus(prev => ({
          ...prev,
          blurDetectionService: blurDetectionResponse.ok ? 'connected' : 'disconnected'
        }))
      } catch {
        setServicesStatus(prev => ({ ...prev, blurDetectionService: 'disconnected' }))
      }
    }

    checkServices()
  }, [])

  const fetchPickerSession = async (userId: string): Promise<string | null> => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_PHOTOS_URL}/sessions/${userId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      })

      const data = await res.json()
      if (data.session) {
        setPickerSessionId(data.session.id)
        return data.session.pickerUri
      } else {
        return null
      }
    } catch (err) {
      console.error("Failed to fetch pickerSession:", err)
      return null
    }
  }

  const fetchMediaItems = async (userId: string, sessionId: string) => {
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_PHOTOS_URL}/mediaItems/${userId}?sessionId=${sessionId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      })
      console.log(r)
      return r.ok
    } catch (err) {
      console.error("Failed to fetch media items:", err)
      return false
    }
  }

  const displayMediaItems = async (userId: string): Promise<Photo[]> => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_PHOTOS_URL}/photos/${userId}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      })
      const data = await res.json()

      if (!data.formattedItems || !Array.isArray(data.formattedItems)) {
        console.error("No media items returned")
        return []
      }

      const formattedItems = data.formattedItems.map((item: any) => ({
        id: item.id,
        filename: item.filename,
        proxyUrl: item.proxyUrl,
        google_created_time: item.google_created_time,
        blur_score: item.blur_score,
        is_blurred: item.is_blurred,
      }))

      return formattedItems ?? []
    } catch (err) {
      console.error("Failed to fetch media items:", err)
      return []
    }
  }

  const analyzePhoto = async (photoId: string, threshold: number = 0.30) => {
    if (!session) return null
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_BLUR_DETECTION_URL}/analyze/${photoId}?user_id=${session.user.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threshold })
      })
      if (!res.ok) throw new Error('Failed to analyze photo')
      const data = await res.json()
      setPhotos(prev => prev.map(p => p.id === photoId ? { ...p, blur_score: data.blur_score, is_blurred: data.is_blurred } : p))
      return data
    } catch (err) {
      console.error('Analyze photo error:', err)
      return null
    }
  }

  const analyzePhotosBatch = async (photoIds: string[], threshold = 0.30) => {
    if (!session) return null
    try {
      console.log(JSON.stringify({
        user_id: session.user.id,
        photo_ids: photoIds,
        threshold
      }))
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BLUR_DETECTION_URL}/analyze/batch`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: session.user.id,
            photo_ids: photoIds,
            threshold
          })
        }
      )
      if (!res.ok) throw new Error('Failed to queue batch analysis')
      const data = await res.json()
      console.log('Batch queued:', data)
      return data
    } catch (err) {
      console.error('Batch analysis error:', err)
      return null
    }
  }

  const handleExpiredPhoto = (photoId: string) => {
    setPhotos(prev =>
      prev.map(p =>
        p.id === photoId ? { ...p, proxyUrl: undefined } : p
      )
    )
    if (!expiredAlertShown.current) {
      expiredAlertShown.current = true
      alert("Some photos have expired. Please open Google Photos Picker to refresh.")
    }
  }

  const createUnblurredAlbum = async (): Promise<void> => {
    if (!session?.user?.id) return alert('Please log in to create an album')

    const unblurredPhotos = photos.filter(p => p.is_blurred === false)
    if (unblurredPhotos.length === 0) return alert('No unblurred photos found to create an album')

    setAlbumLoading(true)
    try {
      const token = session.classifyAccessToken || session.accessToken
      if (!token || token.length < 10) {
        throw new Error('Authentication token is missing. Please sign in again.')
      }
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/photos/google/unblurred-album/${session.user.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || 'Failed to create unblurred album')
      }

      const data = await res.json()
      alert(`Album created!\nTitle: ${data.albumTitle}\nPhotos uploaded: ${data.uploadedCount}`)
    } catch (err) {
      console.error('Error creating unblurred album:', err)
      alert(`Error creating album: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setAlbumLoading(false)
    }
  }


  useEffect(() => {
    const fetchPhotos = async () => {
      if (!session) return
      setPhotosLoading(true)
      setPhotosError(null)
      try {
        const mediaItems = await displayMediaItems(session.user.id)
        if (mediaItems) {
          setPhotos(mediaItems)
        } else {
          setPhotosError('No media items returned.')
        }
      } catch (err) {
        console.error('Failed to fetch photos:', err)
        setPhotosError('Failed to load photos. Please try again.')
      } finally {
        setPhotosLoading(false)
      }
    }

    fetchPhotos()
  }, [session])

  useEffect(() => {
    if (!session) return

    const interval = setInterval(async () => {
      try {
        const mediaItems = await displayMediaItems(session.user.id)
        setPhotos(mediaItems)
      } catch (err) {
        console.error('Failed to fetch photos:', err)
      }
    }, 2000) // Update every 2 seconds

    return () => clearInterval(interval)
  }, [session])

  return (
    <main className="flex bg-gray-50">
      <div className="flex-1 flex flex-col">
        <Header
          session={session}
          fetchPickerSession={fetchPickerSession}
          fetchMediaItems={fetchMediaItems}
          pickerSessionId={pickerSessionId}
          photos={photos}
          setPhotos={setPhotos}
          displayMediaItems={displayMediaItems}
          expiredAlertShown={expiredAlertShown}
        />
        <div className="flex h-screen">
          <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
          <div className="flex-1 overflow-auto p-6">
            {activeTab === 'gallery' && <PhotoGallery photos={photos} photosLoading={photosLoading} photosError={photosError} setPhotos={setPhotos} handleExpiredPhoto={handleExpiredPhoto} analyzePhoto={analyzePhoto} analyzePhotosBatch={analyzePhotosBatch} createUnblurredAlbum={createUnblurredAlbum} albumLoading={albumLoading} />}
            {activeTab === 'stats' && <PhotoStatistics photos={photos} />}
            {activeTab === 'clearGallery' && <PhotoClearGallery photos={photos} photosLoading={photosLoading} photosError={photosError} setPhotos={setPhotos} handleExpiredPhoto={handleExpiredPhoto} />}
            {activeTab === 'blurredGallery' && <PhotoBlurredGallery photos={photos} photosLoading={photosLoading} photosError={photosError} setPhotos={setPhotos} handleExpiredPhoto={handleExpiredPhoto} />}
            {activeTab === 'debug' && <DebugInfo servicesStatus={servicesStatus} />}
          </div>
        </div>
      </div>
    </main>

  )
}
