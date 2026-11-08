export default function ErrorMessage({ message }: { message: string }) {
  return (
    <p role="alert" className="text-sm text-red-700">
      {message}
    </p>
  );
}
