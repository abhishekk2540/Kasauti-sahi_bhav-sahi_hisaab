export const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{7,128}$/;
export const PASSWORD_RULE_MESSAGE = "Password needs 7+ characters, uppercase, lowercase, a number, and a special character.";
export const PASSWORD_HINT = "7+ chars, upper/lowercase, number and special character";