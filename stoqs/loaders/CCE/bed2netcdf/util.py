'''
$Id: util.py 13595 2016-06-16 16:31:02Z mccann $
'''
def quaternConj(q):
    '''
    Translated from Matlab code to Python/Numpy:

    function qConj = quaternConj(q)
    %QUATERN2ROTMAT Converts a quaternion to its conjugate
    %
    %   qConj = quaternConj(q)
    %
    %   Converts a quaternion to its conjugate.
    %
    %   For more information see:
    %   http://www.x-io.co.uk/node/8#quaternions
    %
    %   Date          Author          Notes
    %   27/09/2011    SOH Madgwick    Initial release
    
        qConj = [q(:,1) -q(:,2) -q(:,3) -q(:,4)];
    end
    '''

    return q[0], -q[1], -q[2], -q[3]


def quatern2euler(q):
    '''
    Translated from Matlab code to Python/Numpy:

    function euler = quatern2euler(q)
    %QUATERN2EULER Converts a quaternion orientation to ZYX Euler angles
    %
    %   q = quatern2euler(q)
    %
    %   Converts a quaternion orientation to ZYX Euler angles where phi is a
    %   rotation around X, theta around Y and psi around Z.
    %
    %   For more information see:
    %   http://www.x-io.co.uk/node/8#quaternions
    %
    %   Date          Author          Notes
    %   27/09/2011    SOH Madgwick    Initial release
    
        R(1,1,:) = 2.*q(:,1).^2-1+2.*q(:,2).^2;
        R(2,1,:) = 2.*(q(:,2).*q(:,3)-q(:,1).*q(:,4));
        R(3,1,:) = 2.*(q(:,2).*q(:,4)+q(:,1).*q(:,3));
        R(3,2,:) = 2.*(q(:,3).*q(:,4)-q(:,1).*q(:,2));
        R(3,3,:) = 2.*q(:,1).^2-1+2.*q(:,4).^2;
    
        phi = atan2(R(3,2,:), R(3,3,:) );
        theta = -atan(R(3,1,:) ./ sqrt(1-R(3,1,:).^2) );
        psi = atan2(R(2,1,:), R(1,1,:) );
    
        euler = [phi(1,:)' theta(1,:)' psi(1,:)'];
    end
    '''

    import numpy as np

    q = np.array(q)
    R = np.zeros((3,3))

    R[0,0] = 2 * np.square(q[0]) - 1 + 2 * np.square(q[1])
    R[1,0] = 2 * (q[1] * q[2] - q[0] * q[3])
    R[2,0] = 2 * (q[1] * q[3] + q[0] * q[2])
    R[2,1] = 2 * (q[2] * q[3] - q[0] * q[1])
    R[2,2] = 2 * np.square(q[0]) - 1 + 2 * np.square(q[3])

    phi = np.arctan2(R[2,1], R[2,2])
    theta = -np.arctan(R[2,0] / np.sqrt(1 - np.square(R[2,0])))
    psi = np.arctan2(R[1,0], R[0,0])

    return phi, theta, psi

def quatern2eulervector(q):
    '''
    Translated from Matlab code SpinCalc.m to Python/Numpy:

    %        EV - [m1,m2,m3,MU] (Nx4) row vector list dictating the components of euler
    %             rotation vector (original coordinate frame) and the Euler 
    %             rotation angle about that vector (MU) (DEGREES)
    %
    %        Q - [q1,q2,q3,q4] (Nx4) row vector list defining quaternion of
    %            rotation.  q4 = cos(MU/2) where MU is Euler rotation angle

    case 'EV'
        MU=2*atan2(sqrt(sum(Q(:,1:3).*Q(:,1:3),2)),Q(:,4));
        if sin(MU/2)~=zeros(N,1),
            OUTPUT=[Q(:,1)./sin(MU/2),Q(:,2)./sin(MU/2),Q(:,3)./sin(MU/2),MU*180/pi];
        else
            OUTPUT=NaN(N,4);
            for ii=1:N,
                if sin(MU(ii,1)/2)~=0,
                    OUTPUT(ii,1:4)=[Q(ii,1)/sin(MU(ii,1)/2),Q(ii,2)/sin(MU(ii,1)/2),Q(ii,3)/sin(MU(ii,1)/2),MU(ii,1)*180/pi];
                else
                    OUTPUT(ii,1:4)=[1,0,0,MU(ii,1)*180/pi];
                end
            end
        end

    Python code is scalar based
    '''

    import numpy as np

    ##print q
    mu = 2 * np.arctan2(np.sqrt(np.sum(np.array(q[:3]) * np.array(q[:3]))), np.array(q[3]))
    if np.sin(mu/2) != 0:
        output = [q[0] / np.sin(mu/2), q[1] / np.sin(mu/2), q[2] / np.sin(mu/2), mu * 180/np.pi]
    else:
        output = np.empty(4)
        output[:] = np.nan
        if np.sin(mu/2) != 0:
            output = [q[0] / np.sin(mu/2), q[1] / np.sin(mu/2), q[2] / np.sin(mu/2), mu * 180/np.pi]
        else:
            output = [1, 0, 0, mu * 180/np.pi]

    return output


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    from math import radians, cos, sin, asin, sqrt

    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 

    # 6367 km is the radius of the Earth
    km = 6367 * c
    return km 

if __name__ == '__main__':
    '''
    Test the Qauternion functions
    '''

    pass

