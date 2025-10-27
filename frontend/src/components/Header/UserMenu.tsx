'use client'
import AuthButton from '@/components/AuthButton'
import { Photo } from '@/types'

interface UserMenuProps {
    session: any
    fetchPickerSession: (userId: string) => Promise<string | null>
    fetchMediaItems: (userId: string, sessionId: string) => Promise<boolean>
    pickerSessionId: string
    photos: Photo[]
    setPhotos: (photos: Photo[]) => void
    displayMediaItems: (userId: string) => Promise<Photo[]>
    expiredAlertShown: React.MutableRefObject<boolean>
}

export default function UserMenu({ session, fetchPickerSession, fetchMediaItems, pickerSessionId, photos, setPhotos, displayMediaItems, expiredAlertShown }: UserMenuProps) {
    return (
        <div className="relative group">
            <button className="flex items-center space-x-2 px-3 py-2 rounded hover:bg-gray-100">
                <img src={session?.user.image || '/default-avatar.png'} className="h-8 w-8 rounded-full" />
                <span className="text-gray-600">{session?.user.name || ''}</span>
            </button>
            <div className="absolute right-0 mt-2 w-64 bg-white shadow-lg rounded border border-gray-200 p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-50">
                <div className="mt-4 space-y-2">
                    {session && (
                        <>
                            <button
                                className="w-full px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                                onClick={async () => {
                                    if (session) {
                                        const pickerUri = await fetchPickerSession(session.user.id)
                                        if (pickerUri) window.open(pickerUri, "_blank")
                                        else alert("Picker URL is not available")
                                    }
                                }}
                            >
                                Pick Google Photos
                            </button>
                            <button
                                className="w-full px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                                onClick={async () => {
                                    if (session) {
                                        if (!pickerSessionId) return alert("Please pick photos first")
                                        const isFetched = await fetchMediaItems(session.user.id, pickerSessionId)
                                        if (isFetched) {
                                            expiredAlertShown.current = false
                                            const updatedPhotos = await displayMediaItems(session.user.id)
                                            if (updatedPhotos) setPhotos(updatedPhotos)
                                        } else {
                                            alert("Please try again")
                                        }
                                    }
                                }}
                            >
                                Sync Google Photos
                            </button>
                        </>
                    )}
                    <AuthButton />
                </div>
            </div>
        </div>
    )
}
