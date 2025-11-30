import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { Suspense, useMemo, type FC } from "react";

import { Loader } from "@react-three/drei";
import { Flex } from "@radix-ui/themes";

function* imitateBodyPartSelectGenerator() {
  yield "Right side of the chest";
  yield "Left side of the chest";
  yield "Head";
  yield "Neck";
  yield "Left leg";
  yield "Head";
  while (true) {
    yield "Stomach";
  }
}

const bodyPartGenerator = imitateBodyPartSelectGenerator();

const HumanModel = () => {
  const gltf = useGLTF("/human.glb");

  const scene = useMemo(() => gltf.scene.clone(true), [gltf]);

  const { center } = useMemo(() => {
    const box = new THREE.Box3().setFromObject(gltf.scene);
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    box.getCenter(center);
    box.getSize(size);
    return { center };
  }, [gltf]);

  return (
    <group position={[-center.x, -center.y, -center.z]} scale={1}>
      <primitive object={scene} />
    </group>
  );
};

type HumanSceneProps = {
  selectedBodyPart: string | null;
  handleSelectBodyPart: (bodyPart: string | null) => void;
  isDisabled: boolean;
};

export const HumanScene: FC<HumanSceneProps> = ({
  handleSelectBodyPart,
  isDisabled,
}) => {
  return (
    <Flex
      direction="column"
      flexGrow="1"
      flexBasis="90%"
      onClick={() => {
        if (isDisabled) return;
        handleSelectBodyPart(bodyPartGenerator.next().value ?? null);
      }}
    >
      <Canvas camera={{ position: [0, 1.5, 3], zoom: 3 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[3, 5, 2]} intensity={1} />

        <Suspense fallback={null}>
          <HumanModel />
        </Suspense>

        <OrbitControls />
      </Canvas>
      <Loader containerStyles={{ backgroundColor: "darkgray" }} />
    </Flex>
  );
};
