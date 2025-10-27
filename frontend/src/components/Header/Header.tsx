'use client'
import UserMenu from './UserMenu'
import { Photo } from '@/types'

interface HeaderProps {
    session: any
    fetchPickerSession: (userId: string) => Promise<string | null>
    fetchMediaItems: (userId: string, sessionId: string) => Promise<boolean>
    pickerSessionId: string
    photos: Photo[]
    setPhotos: (photos: Photo[]) => void
    displayMediaItems: (userId: string) => Promise<Photo[]>
    expiredAlertShown: React.MutableRefObject<boolean>
}

export default function Header(props: HeaderProps) {
    return (
        <header className="flex items-center justify-between px-6 py-4 bg-white shadow">
            <div className="flex items-center space-x-2">
                <img src="/logo.png" alt="Classify Logo" className="w-56" />
            </div>
            <UserMenu {...props} />
        </header>
    )
}
