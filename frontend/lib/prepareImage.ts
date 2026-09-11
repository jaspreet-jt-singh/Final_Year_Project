const MAX_BYTES = Math.floor(3.8 * 1024 * 1024)

export async function prepareImage(file: File): Promise<File> {
  if (file.size > 25 * 1024 * 1024) throw new Error('Please choose an image smaller than 25 MiB.')
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    throw new Error('This image could not be opened. Please use JPEG, PNG, or WebP.')
  }
  try {
    if (!bitmap.width || !bitmap.height || bitmap.width * bitmap.height > 25000000) {
      throw new Error('Please choose an image with at most 25 megapixels.')
    }
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * scale))
    canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Your browser could not prepare this image.')
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    for (const quality of [0.92, 0.8, 0.65, 0.5]) {
      const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/jpeg', quality))
      if (blob && blob.size <= MAX_BYTES) return new File([blob], 'food.jpg', { type: 'image/jpeg' })
    }
    throw new Error('This image is too large to upload. Please choose a smaller image.')
  } finally {
    bitmap.close()
  }
}
