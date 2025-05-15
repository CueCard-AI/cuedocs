import e from "express";

export const promiseDone = () => {
  let done: (value: void | PromiseLike<void>) => void = () => {};
  const promise = new Promise<void>((resolve) => {
    done = resolve;
  });

  return { done, promise };
};


// This function is used to get the value of a specific cookie from a cookie string.
function getCookieValue(cookieString: string | undefined, cookieName: string): string | null {
  if (!cookieString) {
    return null;
  }
  const name = cookieName + "=";
  const decodedCookie = decodeURIComponent(cookieString);
  const ca = decodedCookie.split(';');
  for(let i = 0; i <ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return null;
}

export { getCookieValue };