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
