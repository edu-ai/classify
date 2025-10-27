'use client'
import { Photo } from '@/types'

interface PhotoStatisticsProps {
    photos: Photo[]
}

export default function PhotoStatistics({ photos }: PhotoStatisticsProps) {
    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-600 mb-4 text-center">Photo Statistics</h2>
            <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                    <div className="text-2xl font-bold text-blue-600">{photos.length}</div>
                    <div className="text-sm text-gray-600">Total Photos</div>
                </div>
                <div>
                    <div className="text-2xl font-bold text-blue-600">{photos.filter(p => p.is_blurred === false).length}</div>
                    <div className="text-sm text-gray-600">Clear Photos</div>
                </div>
                <div>
                    <div className="text-2xl font-bold text-blue-600">{photos.filter(p => p.is_blurred === true).length}</div>
                    <div className="text-sm text-gray-600">Blurred Photos</div>
                </div>
            </div>
        </div>
    )
}
