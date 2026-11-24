import { describe, expect, it } from 'vitest'
import { cameraService } from '../services'

describe('upload validation', () => {
  it('rejects non-images and files over 8 MB', () => {
    expect(cameraService.validate(new Blob(['x'], { type: 'text/plain' }))).toMatch(/not an image/)
    expect(cameraService.validate(new Blob([new Uint8Array(9 * 1024 * 1024)], { type: 'image/png' }))).toMatch(/larger than 8 MB/)
    expect(cameraService.validate(new Blob([new Uint8Array(10)], { type: 'image/jpeg' }))).toBeNull()
  })
})
