'use client'
import { Photo } from '@/types'
import type { Dispatch, SetStateAction } from 'react'

interface PhotoGalleryProps {
    photos: Photo[]
    photosLoading: boolean
    photosError?: string | null
    setPhotos: Dispatch<SetStateAction<Photo[]>>
    handleExpiredPhoto: (id: string) => void
}

export default function PhotoGallery({ photos, photosLoading, photosError, setPhotos, handleExpiredPhoto }: PhotoGalleryProps) {
    const blurredPhotos = photos.filter(p => p.is_blurred === true)
    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4 text-gray-600">Photo Gallery</h2>
            {photosLoading ? (
                <div className="text-center py-8">
                    <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    <p>Loading photos...</p>
                </div>
            ) : photosError ? (
                <div className="text-center py-8 text-red-500">
                    <p>{photosError}</p>
                    <button
                        className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                        onClick={() => {
                            setPhotos([]);
                        }}
                    >
                        Retry
                    </button>
                </div>
            ) : blurredPhotos.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                    <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="text-lg mb-2">No photos found in database</p>
                    <p className="text-sm">Please pick and sync your photos first.</p>
                </div>
            ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    {blurredPhotos.map((photo) => (
                        <div
                            key={photo.id}
                            className="bg-gray-200 rounded-lg overflow-hidden flex flex-col"
                        >
                            {photo.proxyUrl ? (
                                <>
                                    <div className="aspect-square w-full overflow-hidden">
                                        <img
                                            src={photo.proxyUrl}
                                            alt={photo.filename || 'Photo'}
                                            className="w-full h-full object-cover"
                                            onError={() => handleExpiredPhoto(photo.id)}
                                        />
                                    </div>
                                    <div className="p-2 flex flex-col items-start gap-1">
                                        {photo.blur_score ? (
                                            <>
                                                <p className="text-sm text-gray-600">Blur Score: {photo.blur_score.toFixed(2)}</p>
                                                <p className="text-sm text-gray-600">Is Blurred: {photo.is_blurred ? 'Blurred' : 'Clear'}</p>
                                            </>
                                        ) : (
                                            <>
                                                <p className="text-sm text-gray-600">Blur Score: -</p>
                                                <p className="text-sm text-gray-600">Is Blurred: -</p>
                                            </>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <div className="aspect-square w-full flex items-center justify-center text-gray-400">
                                    <svg
                                        className="w-8 h-8"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                        />
                                    </svg>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

            )}
        </div>
    )
}
