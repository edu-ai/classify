'use client'

interface SidebarProps {
    activeTab: string
    setActiveTab: (tab: string) => void
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
    return (
        <aside className="bg-white shadow-md flex flex-col w-64">
            <nav className="flex-1 mt-4 space-y-2">
                <button className={`w-full text-left px-4 py-2 rounded text-gray-600 ${activeTab === 'gallery' ? 'bg-gray-100' : ''}`} onClick={() => setActiveTab('gallery')}>
                    Photo Gallery
                </button>
                <button className={`w-full text-left px-4 py-2 rounded text-gray-600 ${activeTab === 'stats' ? 'bg-gray-100' : ''}`} onClick={() => setActiveTab('stats')}>
                    Photo Statistics
                </button>
                <button className={`w-full text-left px-4 py-2 rounded text-gray-600 ${activeTab === 'clearGallery' ? 'bg-gray-100' : ''}`} onClick={() => setActiveTab('clearGallery')}>
                    Clear Photo Gallery
                </button>
                <button className={`w-full text-left px-4 py-2 rounded text-gray-600 ${activeTab === 'blurredGallery' ? 'bg-gray-100' : ''}`} onClick={() => setActiveTab('blurredGallery')}>
                    Blurred Photo Gallery
                </button>
                <button className={`w-full text-left px-4 py-2 rounded text-gray-600 ${activeTab === 'tagGallery' ? 'bg-gray-100' : ''}`} onClick={() => setActiveTab('tagGallery')}>
                    Tagged Photo Gallery
                </button>
                <button className={`w-full text-left px-4 py-2 rounded text-gray-600 ${activeTab === 'debug' ? 'bg-gray-100' : ''}`} onClick={() => setActiveTab('debug')}>
                    Debug Info
                </button>
            </nav>
        </aside>
    )
}
