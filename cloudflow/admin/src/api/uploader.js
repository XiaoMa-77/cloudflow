import {
  checkInstantUploadApi,
  completeChunkUploadApi,
  initChunkUploadApi,
  uploadChunkApi,
  uploadFileApi,
} from './files'

const CHUNK_SIZE = 4 * 1024 * 1024 // 4MB 分片
const DIRECT_UPLOAD_LIMIT = 8 * 1024 * 1024 // ≤8MB 直接整文件上传
const HASH_MAX_SIZE = 64 * 1024 * 1024 // ≤64MB 计算整文件哈希（超出则跳过秒传，改由服务端合并后去重）
const MAX_CHUNK_RETRIES = 3

/**
 * 计算文件 SHA-256（Web Crypto），返回 hex 字符串；文件过大或环境不支持时返回空串。
 */
async function computeSha256(file) {
  if (file.size > HASH_MAX_SIZE || !window.crypto?.subtle) {
    return ''
  }
  try {
    const buffer = await file.arrayBuffer()
    const digest = await window.crypto.subtle.digest('SHA-256', buffer)
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, '0'))
      .join('')
  } catch (error) {
    return ''
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * 智能上传：秒传 → 直传 → 分片断点续传。
 *
 * @param {File} file 待上传文件
 * @param {number|null} parentId 目标目录 id
 * @param {(state: {phase: string, percent: number}) => void} onProgress 进度回调
 *   phase: hashing | instant | uploading | merging | done
 * @returns {Promise<{entry: object, instant: boolean}>}
 */
export async function smartUploadFile({ file, parentId, onProgress }) {
  const report = (phase, percent) => onProgress?.({ phase, percent })

  // 1. 计算内容指纹并尝试秒传
  let contentHash = ''
  if (file.size > 0) {
    report('hashing', 5)
    contentHash = await computeSha256(file)
  }
  if (contentHash) {
    const check = await checkInstantUploadApi({
      fileName: file.name,
      fileSize: file.size,
      contentHash,
      parentId,
    })
    if (check?.instant) {
      report('instant', 100)
      return { entry: check.entry, instant: true }
    }
  }

  // 2. 小文件直接上传
  if (file.size <= DIRECT_UPLOAD_LIMIT) {
    report('uploading', 40)
    const entry = await uploadFileApi({ file, parentId })
    report('done', 100)
    return { entry, instant: false }
  }

  // 3. 大文件分片上传（支持断点续传）
  report('uploading', 8)
  const session = await initChunkUploadApi({
    fileName: file.name,
    fileSize: file.size,
    chunkSize: CHUNK_SIZE,
    contentHash,
    parentId,
  })

  const uploaded = new Set(session.uploadedChunks || [])
  const totalChunks = session.totalChunks || Math.ceil(file.size / CHUNK_SIZE)
  let received = uploaded.size

  for (let index = 0; index < totalChunks; index += 1) {
    if (uploaded.has(index)) {
      continue
    }

    const chunk = file.slice(index * CHUNK_SIZE, Math.min((index + 1) * CHUNK_SIZE, file.size))
    let lastError = null
    for (let attempt = 1; attempt <= MAX_CHUNK_RETRIES; attempt += 1) {
      try {
        await uploadChunkApi({ uploadId: session.uploadId, chunkIndex: index, chunk })
        lastError = null
        break
      } catch (error) {
        lastError = error
        if (attempt < MAX_CHUNK_RETRIES) {
          await sleep(600 * attempt)
        }
      }
    }
    if (lastError) {
      throw lastError
    }

    received += 1
    report('uploading', 8 + Math.round((received / totalChunks) * 87))
  }

  report('merging', 96)
  const entry = await completeChunkUploadApi({ uploadId: session.uploadId })
  report('done', 100)
  return { entry, instant: false }
}
