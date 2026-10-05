import {staffingIndex} from '../../lib/headcountData';
export const prerender = true;
export function GET(): Response {
  return new Response(JSON.stringify(staffingIndex()), {headers: {'Content-Type': 'application/json; charset=utf-8'}});
}
