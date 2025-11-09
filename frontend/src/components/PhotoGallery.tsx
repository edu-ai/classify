'use client'
import { Photo } from '@/types'
import type { Dispatch, SetStateAction } from 'react'

interface PhotoGalleryProps {
    photos: Photo[]
    photosLoading: boolean
    photosError?: string | null
    setPhotos: Dispatch<SetStateAction<Photo[]>>
    handleExpiredPhoto: (id: string) => void
    labelPhoto: (photoId: string) => void
    analyzePhoto: (photoId: string) => void
    analyzePhotosBatch: (photoIds: string[], threshold?: number) => Promise<any>
    createUnblurredAlbum: () => Promise<void>
    albumLoading: boolean
}

export default function PhotoGallery({
    photos,
    photosLoading,
    photosError,
    setPhotos,
    handleExpiredPhoto,
    labelPhoto,
    analyzePhoto,
    analyzePhotosBatch,
    createUnblurredAlbum,
    albumLoading
}: PhotoGalleryProps) {
    return (
        <>
            {/* Flow */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 className="text-xl font-semibold mb-4 text-gray-600">Flow</h2>
                <ol className="list-decimal list-inside space-y-2 text-gray-700">
                    <li>
                        <strong>OAuth Sign Up:</strong> Log in with your Google account.
                        <br />
                        <span className="text-sm text-gray-500">Estimated time: a few seconds</span>
                    </li>
                    <li>
                        <strong>Pick Photos:</strong> Click the「Pick Google Photos」button under your user icon, and select photos from Google Photos in the newly opened tab.
                        <br />
                        <span className="text-sm text-gray-500">Estimated time: a few seconds</span>
                    </li>
                    <li>
                        <strong>Sync Photos:</strong> Click the「Sync Photos」 button under your user icon to sync the selected photos in the separate tab.
                        <br />
                        <span className="text-sm text-gray-500">Estimated time: a few seconds to several tens of seconds depending on the number of photos</span>
                    </li>
                    <li>
                        <strong>Analyze Photos:</strong> Click the 「Detect Blur」 button on each photo to run blur detection.
                        <br />
                        <span className="text-sm text-gray-500">Estimated time: a few hundred milliseconds to 1 second per photo</span>
                    </li>
                    <li>
                        <strong>Tag Photos:</strong> Click the 「Label tag」 button on each photo to automatically generate descriptive tags. These tags help categorize and filter your photos in the gallery.
                        <br />
                        <span className="text-sm text-gray-500">Estimated time: a few hundred milliseconds to 1 second per photo</span>
                    </li>
                    <li>
                        <strong>Create Unblurred Album:</strong> After detecting blur, click the 「Create Unblurred Album」 button to collect all unblurred photos into a Google Photos album.
                        <br />
                        <span className="text-sm text-gray-500">Estimated time: a few seconds to a minute depending on the number of photos</span>
                    </li>
                </ol>
            </div>

            {/* Photo Gallery */}
            <div className="bg-white rounded-lg shadow-md p-6 relative">
                <h2 className="text-xl font-semibold mb-4 text-gray-600">Photo Gallery</h2>

                {/* Top-right buttons */}
                <div className="absolute top-6 right-6 flex gap-2">
                    <button
                        className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-semibold rounded"
                        onClick={() => analyzePhotosBatch(photos.map(p => p.id))}
                    >
                        Detect All Blur
                    </button>
                    <button
                        onClick={createUnblurredAlbum}
                        disabled={albumLoading}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {albumLoading ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                Creating Album...
                            </>
                        ) : (
                            'Create Unblurred Album'
                        )}
                    </button>
                </div>

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
                            onClick={() => setPhotos([])}
                        >
                            Retry
                        </button>
                    </div>
                ) : photos.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        <p className="text-lg mb-2">No photos found in database</p>
                        <p className="text-sm">Please pick and sync your photos first.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mt-12">
                        {photos.map((photo) => (
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
                                                    <p className="text-sm text-gray-600">Status: {photo.is_blurred ? 'Blurred' : 'Clear'}</p>
                                                </>
                                            ) : (
                                                <>
                                                    <p className="text-sm text-gray-600">Blur Score: -</p>
                                                    <p className="text-sm text-gray-600">Status: -</p>
                                                </>
                                            )}
                                            {photo.tag ? (
                                                <>
                                                    <p className="text-sm text-gray-600">Tag: {photo.tag}</p>
                                                </>
                                            ) : (
                                                <>
                                                    <p className="text-sm text-gray-600">Tag: -</p>
                                                </>
                                            )}
                                            <button
                                                className="w-full px-3 py-2 text-white text-sm font-semibold rounded mt-1 bg-blue-500 hover:bg-blue-600"
                                                onClick={() => labelPhoto(photo.id)}
                                            >
                                                Label tag
                                            </button>
                                            <button
                                                className="w-full px-3 py-2 text-white text-sm font-semibold rounded mt-1 bg-blue-500 hover:bg-blue-600"
                                                onClick={() => analyzePhoto(photo.id)}
                                            >
                                                Detect Blur
                                            </button>
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
        </>
    )
}
