// Centered phone-first page shell in the style of the original invite page.
export default function Screen({ title, children }) {
  return (
    <main className="min-h-screen bg-rose-50 font-sans flex flex-col items-center justify-center gap-5 p-4 text-center text-rose-900">
      <h1 className="font-display italic text-4xl text-rose-600">{title}</h1>
      {children}
    </main>
  )
}

export function Button(props) {
  return (
    <button
      {...props}
      className="rounded-full bg-rose-500 px-6 py-3 font-bold text-white shadow-md active:scale-95 disabled:opacity-50"
    />
  )
}

export function Input(props) {
  return <input {...props} className="w-64 rounded-xl border border-rose-200 bg-white px-4 py-3 text-center outline-rose-400" />
}

export function LinkButton(props) {
  return <button {...props} className="text-sm text-rose-500 underline" />
}
