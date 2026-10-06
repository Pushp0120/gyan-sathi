import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

// Latin letters glued onto a Gujarati word (e.g. "સંસાધનACHE") are model glitches.
// Gujarati digits are excluded so units like "૫cm" survive.
const ATTACHED_LATIN = /(?<=[\u0A80-\u0AE5\u0AF0-\u0AFF])[A-Za-z]{2,}/g

export function cleanGujarati(text: string): string {
  return text.replace(ATTACHED_LATIN, '')
}

export default function Markdown({ text }: { text: string }) {
  return (
    <div className="md-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
      >
        {cleanGujarati(text)}
      </ReactMarkdown>
    </div>
  )
}
