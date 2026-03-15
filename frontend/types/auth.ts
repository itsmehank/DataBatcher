export type LoginResponse = {
  accessToken: string;
  admin: { id: string; username: string };
};

export type MeResponse = {
  adminId: string;
  username: string;
};
