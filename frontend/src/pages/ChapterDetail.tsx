import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'

/** Old chapter detail page — now redirects straight into the reader. */
export default function ChapterDetail() {
  const { chapterId } = useParams()
  const navigate = useNavigate()

  useEffect(() => {
    if (chapterId) navigate(`/read/${chapterId}`, { replace: true })
  }, [chapterId, navigate])

  return null
}
