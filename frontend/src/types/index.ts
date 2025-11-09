export interface Photo {
    id: string
    google_photo_id?: string
    filename?: string
    google_created_time?: string
    blur_score?: number
    is_blurred?: boolean
    proxyUrl?: string
    tag?: string
}

export interface ServicesStatus {
    apiGateway: string
    authService: string
    photosService: string
    blurDetectionService: string
}
