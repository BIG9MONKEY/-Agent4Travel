<template>
  <div class="file-upload">
    <input
      type="file"
      ref="fileInput"
      accept=".pdf"
      @change="handleFileChange"
      style="display: none"
    />
    <div class="button-group">
      <button class="upload-button" @click="triggerFileInput">
        <span class="upload-icon">📄</span>
        上传PDF文件
      </button>
      <button class="create-rag-button" @click="createRag" :disabled="isCreating">
        <span class="rag-icon">📚</span>
        {{ isCreating ? '创建中...' : '创建RAG知识库' }}
      </button>
    </div>
    <div v-if="uploadStatus" :class="['upload-status', uploadStatus.type]">
      {{ uploadStatus.message }}
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const fileInput = ref(null)
const uploadStatus = ref(null)
const isCreating = ref(false)

const triggerFileInput = () => {
  fileInput.value.click()
}

const createRag = async () => {
  try {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      uploadStatus.value = {
        type: 'error',
        message: '请先登录'
      }
      return
    }

    isCreating.value = true
    uploadStatus.value = {
      type: 'info',
      message: '正在创建RAG知识库...'
    }

    const response = await fetch('http://localhost:3200/create-rag', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      const data = await response.json()
      uploadStatus.value = {
        type: 'success',
        message: data.message || 'RAG知识库创建成功'
      }
    } else {
      const errorData = await response.json()
      throw new Error(errorData.message || '创建失败')
    }
  } catch (error) {
    uploadStatus.value = {
      type: 'error',
      message: '创建RAG知识库失败：' + error.message
    }
  } finally {
    isCreating.value = false
    // 3秒后清除状态消息
    setTimeout(() => {
      uploadStatus.value = null
    }, 3000)
  }
}

const handleFileChange = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  if (file.type !== 'application/pdf') {
    uploadStatus.value = {
      type: 'error',
      message: '请选择PDF文件'
    }
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  try {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      uploadStatus.value = {
        type: 'error',
        message: '请先登录'
      }
      return
    }

    const response = await fetch('http://localhost:3200/upload-pdf', {
      method: 'POST',
      body: formData,
      headers: {
        'Accept': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      uploadStatus.value = {
        type: 'success',
        message: '文件上传成功'
      }
    } else {
      const errorData = await response.json()
      throw new Error(errorData.message || '上传失败')
    }
  } catch (error) {
    uploadStatus.value = {
      type: 'error',
      message: '文件上传失败：' + error.message
    }
  }

  // 3秒后清除状态消息
  setTimeout(() => {
    uploadStatus.value = null
  }, 3000)
}
</script>

<style scoped>
.file-upload {
  margin: 10px;
  text-align: center;
}

.button-group {
  
  margin-top: 20px;
  display: flex;
  gap: 20px;
  justify-content: center;
  margin-bottom: 10px;
}

.upload-button, .create-rag-button {
  background-color: #1976d2;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 0 auto;
  transition: background-color 0.3s;
  min-width: 120px;
}

.upload-button:hover, .create-rag-button:hover {
  background-color: #1565c0;
}

.create-rag-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.upload-icon, .rag-icon {
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-status {
  margin-top: 8px;
  padding: 8px;
  border-radius: 4px;
}

.upload-status.success {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.upload-status.error {
  background-color: #ffebee;
  color: #c62828;
}

.upload-status.info {
  background-color: #e3f2fd;
  color: #1976d2;
}
</style> 