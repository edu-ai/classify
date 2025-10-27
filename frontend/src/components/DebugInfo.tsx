'use client'
import { ServicesStatus } from '@/types'

interface DebugInfoProps {
    servicesStatus: ServicesStatus
}

export default function DebugInfo({ servicesStatus }: DebugInfoProps) {
    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-gray-600 mb-4 text-center">Debug Info</h2>
                <div className="flex justify-between">
                    <span className="text-gray-600">API Gateway:</span>
                    <span className={`font-medium ${servicesStatus.apiGateway === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
                        {servicesStatus.apiGateway}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-600">Auth Service:</span>
                    <span className={`font-medium ${servicesStatus.authService === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
                        {servicesStatus.authService}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-600">Photos Service:</span>
                    <span className={`font-medium ${servicesStatus.photosService === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
                        {servicesStatus.photosService}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span className="text-gray-600">Blur Detection Service:</span>
                    <span className={`font-medium ${servicesStatus.blurDetectionService === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
                        {servicesStatus.blurDetectionService}
                    </span>
                </div>
            </div>
        </div>
    )
}
