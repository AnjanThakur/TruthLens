import 'server-only';
export function whatsappLink() {
  const number = process.env.WHATSAPP_PUBLIC_NUMBER;
  if (process.env.WHATSAPP_LINK_ENABLED !== 'true' || !number || !/^[1-9]\d{6,14}$/.test(number))
    return null;
  return `https://wa.me/${number}`;
}
